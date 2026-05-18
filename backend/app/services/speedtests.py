from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean

from sqlalchemy import Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.core.config import settings
from backend.app.models import AlertEvent, Server, Severity, SpeedTestResult, SpeedTestStatus
from backend.app.schemas.speed_test import AgentSpeedTestCompleteRequest
from backend.app.services.notifier import TelegramNotifier


@dataclass(slots=True)
class SpeedBaseline:
    download_mbps: float | None
    upload_mbps: float | None
    ping_ms: float | None
    download_samples: int
    upload_samples: int
    ping_samples: int


class SpeedTestService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.notifier = TelegramNotifier()

    async def queue_speed_test(self, server_id: int) -> tuple[SpeedTestResult, bool]:
        async with self.session_factory() as session:
            server = await session.get(Server, server_id)
            if not server:
                raise LookupError("Server not found")

            existing = await session.scalar(
                select(SpeedTestResult)
                .where(
                    SpeedTestResult.server_id == server_id,
                    SpeedTestResult.status.in_([SpeedTestStatus.PENDING, SpeedTestStatus.RUNNING]),
                )
                .order_by(SpeedTestResult.created_at.desc())
            )
            if existing:
                return existing, False

            item = SpeedTestResult(server_id=server_id, status=SpeedTestStatus.PENDING)
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item, True

    async def claim_next(self, server_id: int | None, server_name: str | None) -> SpeedTestResult | None:
        async with self.session_factory() as session:
            server = await self._resolve_server(session, server_id, server_name)
            if not server:
                raise LookupError("Server not found")

            statement: Select[tuple[SpeedTestResult]] = (
                select(SpeedTestResult)
                .where(
                    SpeedTestResult.server_id == server.id,
                    SpeedTestResult.status == SpeedTestStatus.PENDING,
                )
                .order_by(SpeedTestResult.created_at.asc())
                .limit(1)
            )
            item = await session.scalar(statement)
            if not item:
                return None

            item.status = SpeedTestStatus.RUNNING
            item.started_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(item)
            return item

    async def complete(self, speed_test_id: int, payload: AgentSpeedTestCompleteRequest) -> SpeedTestResult:
        async with self.session_factory() as session:
            item = await session.get(SpeedTestResult, speed_test_id)
            if not item:
                raise LookupError("Speed test task not found")
            server = await session.get(Server, item.server_id)
            if not server:
                raise LookupError("Server not found")

            item.status = payload.status
            item.provider_name = payload.provider_name
            item.provider_location = payload.provider_location
            item.external_ip = payload.external_ip
            item.download_mbps = payload.download_mbps
            item.upload_mbps = payload.upload_mbps
            item.ping_ms = payload.ping_ms
            item.jitter_ms = payload.jitter_ms
            item.details = payload.details
            item.error = payload.error
            item.completed_at = datetime.now(timezone.utc)
            if item.started_at is None:
                item.started_at = item.completed_at

            await self._maybe_emit_speed_events(session, server, item)
            await session.commit()
            await session.refresh(item)
            return item

    async def latest_for_server(self, server_id: int) -> SpeedTestResult | None:
        async with self.session_factory() as session:
            server = await session.get(Server, server_id)
            if not server:
                raise LookupError("Server not found")
            return await session.scalar(
                select(SpeedTestResult)
                .where(SpeedTestResult.server_id == server_id)
                .order_by(SpeedTestResult.created_at.desc())
            )

    async def list_for_server(self, server_id: int, limit: int = 10) -> list[SpeedTestResult]:
        async with self.session_factory() as session:
            server = await session.get(Server, server_id)
            if not server:
                raise LookupError("Server not found")
            items = (
                await session.scalars(
                    select(SpeedTestResult)
                    .where(SpeedTestResult.server_id == server_id)
                    .order_by(SpeedTestResult.created_at.desc())
                    .limit(max(1, min(limit, 50)))
                )
            ).all()
            return list(items)

    @staticmethod
    async def _resolve_server(
        session: AsyncSession,
        server_id: int | None,
        server_name: str | None,
    ) -> Server | None:
        if server_id:
            return await session.get(Server, server_id)
        if server_name:
            return await session.scalar(select(Server).where(func.lower(Server.name) == server_name.lower()))
        return None

    async def _maybe_emit_speed_events(
        self,
        session: AsyncSession,
        server: Server,
        item: SpeedTestResult,
    ) -> None:
        if item.status != SpeedTestStatus.COMPLETED:
            return
        if not settings.speed_test_degradation_alert_enabled:
            return

        baseline = await self._build_baseline(session, server.id, item.id)
        if not baseline:
            return

        severity, message = self._build_degradation_message(server, item, baseline)
        if severity is not None and message is not None:
            event_type = "speed-critical" if severity == Severity.CRITICAL else "speed-warning"
            if not await self._has_recent_event(
                session,
                server.id,
                [event_type],
                timedelta(minutes=settings.speed_test_alert_cooldown_minutes),
            ):
                await self._emit_speed_event(session, server, severity, event_type, message)
            return

        await self._maybe_emit_recovery(session, server, item)

    async def _build_baseline(
        self,
        session: AsyncSession,
        server_id: int,
        current_speed_test_id: int,
    ) -> SpeedBaseline | None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.speed_test_baseline_window_hours)
        sample_limit = max(
            settings.speed_test_baseline_samples * 3,
            settings.speed_test_baseline_min_samples * 3,
        )
        history = (
            await session.scalars(
                select(SpeedTestResult)
                .where(
                    SpeedTestResult.server_id == server_id,
                    SpeedTestResult.id != current_speed_test_id,
                    SpeedTestResult.status == SpeedTestStatus.COMPLETED,
                    SpeedTestResult.completed_at.is_not(None),
                    SpeedTestResult.completed_at >= cutoff,
                )
                .order_by(SpeedTestResult.completed_at.desc())
                .limit(sample_limit)
            )
        ).all()

        download_values = [
            item.download_mbps
            for item in history
            if item.download_mbps is not None and item.download_mbps > 0
        ][: settings.speed_test_baseline_samples]
        upload_values = [
            item.upload_mbps
            for item in history
            if item.upload_mbps is not None and item.upload_mbps > 0
        ][: settings.speed_test_baseline_samples]
        ping_values = [
            item.ping_ms
            for item in history
            if item.ping_ms is not None and item.ping_ms > 0
        ][: settings.speed_test_baseline_samples]

        if max(len(download_values), len(upload_values), len(ping_values)) < settings.speed_test_baseline_min_samples:
            return None

        return SpeedBaseline(
            download_mbps=mean(download_values) if len(download_values) >= settings.speed_test_baseline_min_samples else None,
            upload_mbps=mean(upload_values) if len(upload_values) >= settings.speed_test_baseline_min_samples else None,
            ping_ms=mean(ping_values) if len(ping_values) >= settings.speed_test_baseline_min_samples else None,
            download_samples=len(download_values),
            upload_samples=len(upload_values),
            ping_samples=len(ping_values),
        )

    def _build_degradation_message(
        self,
        server: Server,
        item: SpeedTestResult,
        baseline: SpeedBaseline,
    ) -> tuple[Severity | None, str | None]:
        critical_reasons: list[str] = []
        warning_reasons: list[str] = []

        if item.download_mbps is not None and baseline.download_mbps:
            ratio = item.download_mbps / baseline.download_mbps
            if ratio <= settings.speed_test_critical_ratio:
                critical_reasons.append(
                    f"download {item.download_mbps:.1f} Mbps vs usual {baseline.download_mbps:.1f} Mbps"
                )
            elif ratio <= settings.speed_test_warning_ratio:
                warning_reasons.append(
                    f"download {item.download_mbps:.1f} Mbps vs usual {baseline.download_mbps:.1f} Mbps"
                )

        if item.upload_mbps is not None and baseline.upload_mbps:
            ratio = item.upload_mbps / baseline.upload_mbps
            if ratio <= settings.speed_test_critical_ratio:
                critical_reasons.append(
                    f"upload {item.upload_mbps:.1f} Mbps vs usual {baseline.upload_mbps:.1f} Mbps"
                )
            elif ratio <= settings.speed_test_warning_ratio:
                warning_reasons.append(
                    f"upload {item.upload_mbps:.1f} Mbps vs usual {baseline.upload_mbps:.1f} Mbps"
                )

        if item.ping_ms is not None and baseline.ping_ms:
            multiplier = item.ping_ms / baseline.ping_ms
            if multiplier >= settings.speed_test_ping_critical_multiplier:
                critical_reasons.append(
                    f"ping {item.ping_ms:.1f} ms vs usual {baseline.ping_ms:.1f} ms"
                )
            elif multiplier >= settings.speed_test_ping_warning_multiplier:
                warning_reasons.append(
                    f"ping {item.ping_ms:.1f} ms vs usual {baseline.ping_ms:.1f} ms"
                )

        if critical_reasons:
            return (
                Severity.CRITICAL,
                f"Speed test critical on {server.name}: {'; '.join(critical_reasons)}.",
            )
        if warning_reasons:
            return (
                Severity.WARNING,
                f"Speed test degraded on {server.name}: {'; '.join(warning_reasons)}.",
            )
        return None, None

    async def _maybe_emit_recovery(
        self,
        session: AsyncSession,
        server: Server,
        item: SpeedTestResult,
    ) -> None:
        latest_speed_issue = await session.scalar(
            select(AlertEvent)
            .where(
                AlertEvent.server_id == server.id,
                AlertEvent.event_type.in_(["speed-warning", "speed-critical"]),
                AlertEvent.created_at >= datetime.now(timezone.utc)
                - timedelta(hours=settings.speed_test_recovery_window_hours),
            )
            .order_by(desc(AlertEvent.created_at))
        )
        if not latest_speed_issue:
            return

        latest_recovery = await session.scalar(
            select(AlertEvent)
            .where(AlertEvent.server_id == server.id, AlertEvent.event_type == "speed-recovery")
            .order_by(desc(AlertEvent.created_at))
        )
        if latest_recovery and latest_recovery.created_at >= latest_speed_issue.created_at:
            return

        message = (
            f"Speed test recovered on {server.name}: "
            f"download {self._fmt_speed(item.download_mbps)}, "
            f"upload {self._fmt_speed(item.upload_mbps)}, "
            f"ping {self._fmt_ping(item.ping_ms)}."
        )
        await self._emit_speed_event(session, server, Severity.INFO, "speed-recovery", message)

    async def _has_recent_event(
        self,
        session: AsyncSession,
        server_id: int,
        event_types: list[str],
        cooldown: timedelta,
    ) -> bool:
        cutoff = datetime.now(timezone.utc) - cooldown
        existing = await session.scalar(
            select(AlertEvent)
            .where(
                AlertEvent.server_id == server_id,
                AlertEvent.event_type.in_(event_types),
                AlertEvent.created_at >= cutoff,
            )
            .order_by(desc(AlertEvent.created_at))
        )
        return existing is not None

    async def _emit_speed_event(
        self,
        session: AsyncSession,
        server: Server,
        severity: Severity,
        event_type: str,
        message: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        is_muted = server.muted_until is not None and server.muted_until > now
        event = AlertEvent(
            server_id=server.id,
            service_check_id=None,
            severity=severity,
            event_type=event_type,
            message=message[:500],
            sent_to_telegram=False,
        )
        session.add(event)

        if is_muted:
            return

        event.sent_to_telegram = await self.notifier.send(event.message)

    @staticmethod
    def _fmt_speed(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.1f} Mbps"

    @staticmethod
    def _fmt_ping(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.1f} ms"
