import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.core.config import settings
from backend.app.models import CheckResult, CheckType, Server, ServerStatus, ServiceCheck, Severity
from backend.app.services.alerting import AlertManager
from backend.app.utils.ping import PingStats, run_icmp_ping
from backend.app.utils.service_checks import ServiceProbeResult, check_http, check_ssl_expiry, check_tcp


logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self._lock = asyncio.Lock()

    async def run_due_checks(self) -> None:
        if self._lock.locked():
            return

        async with self._lock:
            now = datetime.now(timezone.utc)
            try:
                async with self.session_factory() as session:
                    servers = (await session.scalars(select(Server))).all()
                    checks = (await session.scalars(select(ServiceCheck))).all()
            except SQLAlchemyError as exc:
                logger.warning(
                    "Monitoring scheduler skipped because database schema is not ready. Run Alembic migrations first. Details: %s",
                    exc,
                )
                return

            for server in servers:
                if self._is_due(server.last_check_at, server.check_interval_seconds, now):
                    await self.run_server_check(server.id)

            for service_check in checks:
                if self._is_due(service_check.last_check_at, service_check.interval_seconds, now):
                    await self.run_service_check(service_check.id)

    async def run_server_check(self, server_id: int) -> Server | None:
        async with self.session_factory() as session:
            server = await session.get(Server, server_id)
            if not server:
                return None

            previous_status = server.status
            previous_issues = server.consecutive_issues

            ping_stats = await run_icmp_ping(
                server.address,
                attempts=settings.ping_attempts,
                timeout=settings.ping_timeout_seconds,
            )
            status, severity, message = self._classify_ping(server, ping_stats)

            server.status = status
            server.last_check_at = datetime.now(timezone.utc)
            server.last_latency_ms = ping_stats.avg_latency_ms
            server.last_packet_loss = ping_stats.packet_loss
            server.last_jitter_ms = ping_stats.jitter_ms
            server.consecutive_issues = 0 if status == ServerStatus.ONLINE else previous_issues + 1

            session.add(
                CheckResult(
                    server_id=server.id,
                    check_type=CheckType.ICMP,
                    status=status,
                    severity=severity,
                    avg_latency_ms=ping_stats.avg_latency_ms,
                    min_latency_ms=ping_stats.min_latency_ms,
                    max_latency_ms=ping_stats.max_latency_ms,
                    jitter_ms=ping_stats.jitter_ms,
                    packet_loss=ping_stats.packet_loss,
                    message=message,
                    details={"raw": ping_stats.raw_output, "error": ping_stats.error},
                )
            )

            await AlertManager(session).handle_server_transition(
                server=server,
                previous_status=previous_status,
                previous_issues=previous_issues,
                severity=severity,
                message=message,
            )

            await session.commit()
            await session.refresh(server)
            return server

    async def run_service_check(self, service_check_id: int) -> ServiceCheck | None:
        async with self.session_factory() as session:
            service_check = await session.get(ServiceCheck, service_check_id)
            if not service_check:
                return None

            previous_status = service_check.status
            previous_issues = service_check.consecutive_issues
            result = await self._probe_service(service_check)

            service_check.status = result.status
            service_check.last_check_at = datetime.now(timezone.utc)
            service_check.last_response_ms = result.response_time_ms
            service_check.last_status_code = result.status_code
            service_check.last_error = None if result.status == ServerStatus.ONLINE else result.message
            service_check.consecutive_issues = (
                0 if result.status == ServerStatus.ONLINE else previous_issues + 1
            )

            session.add(
                CheckResult(
                    server_id=service_check.server_id,
                    service_check_id=service_check.id,
                    check_type=service_check.check_type,
                    status=result.status,
                    severity=result.severity,
                    response_time_ms=result.response_time_ms,
                    status_code=result.status_code,
                    message=result.message,
                    details=result.details,
                )
            )

            await AlertManager(session).handle_service_transition(
                service_check=service_check,
                previous_status=previous_status,
                previous_issues=previous_issues,
                severity=result.severity,
                message=result.message,
            )

            await session.commit()
            await session.refresh(service_check)
            return service_check

    async def _probe_service(self, service_check: ServiceCheck) -> ServiceProbeResult:
        if service_check.check_type == CheckType.HTTP:
            return await check_http(
                target=service_check.target,
                path=service_check.path,
                expected_status=service_check.expected_status,
                timeout_seconds=service_check.timeout_seconds,
            )
        if service_check.check_type == CheckType.TCP:
            port = service_check.port or 80
            return await check_tcp(
                target=service_check.target,
                port=port,
                timeout_seconds=service_check.timeout_seconds,
            )
        if service_check.check_type == CheckType.SSL:
            return await check_ssl_expiry(
                target=service_check.target,
                port=service_check.port or 443,
                timeout_seconds=service_check.timeout_seconds,
                warning_days=service_check.ssl_expiry_warning_days,
            )
        return ServiceProbeResult(
            status=ServerStatus.UNKNOWN,
            severity=Severity.WARNING,
            response_time_ms=None,
            status_code=None,
            message=f"Unsupported check type {service_check.check_type.value}",
            details={},
        )

    def _classify_ping(self, server: Server, ping_stats: PingStats) -> tuple[ServerStatus, Severity, str]:
        if ping_stats.error or ping_stats.packet_loss >= 100:
            return ServerStatus.OFFLINE, Severity.CRITICAL, "Host is unreachable over ICMP"

        avg_latency = ping_stats.avg_latency_ms or 0.0
        if (
            ping_stats.packet_loss >= server.packet_loss_critical
            or avg_latency >= server.latency_critical_ms
        ):
            return (
                ServerStatus.DEGRADED,
                Severity.CRITICAL,
                f"Latency {avg_latency:.1f} ms, packet loss {ping_stats.packet_loss:.1f}%",
            )

        if (
            ping_stats.packet_loss >= server.packet_loss_warning
            or avg_latency >= server.latency_warning_ms
            or ping_stats.packet_loss > 0
        ):
            return (
                ServerStatus.DEGRADED,
                Severity.WARNING,
                f"Latency {avg_latency:.1f} ms, packet loss {ping_stats.packet_loss:.1f}%",
            )

        return (
            ServerStatus.ONLINE,
            Severity.INFO,
            f"Latency {avg_latency:.1f} ms, jitter {(ping_stats.jitter_ms or 0.0):.1f} ms",
        )

    @staticmethod
    def _is_due(last_check_at: datetime | None, interval_seconds: int, now: datetime) -> bool:
        if not last_check_at:
            return True
        return last_check_at <= now - timedelta(seconds=interval_seconds)
