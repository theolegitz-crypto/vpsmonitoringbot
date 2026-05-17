from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from backend.app.models import AlertEvent, CheckResult, Incident, Server, ServerStatus
from backend.app.schemas.common import AlertEventRead, CheckResultRead, HistoryPoint, IncidentRead, MetricPoint
from backend.app.schemas.server import OverviewResponse, OverviewSummary, ServerCard, ServerDetail


class DashboardService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def build_overview(self) -> OverviewResponse:
        async with self.session_factory() as session:
            servers = (
                (
                    await session.scalars(
                        select(Server).options(selectinload(Server.service_checks)).order_by(Server.name.asc())
                    )
                )
                .unique()
                .all()
            )
            cards = [await self._build_server_card(session, server) for server in servers]
            incidents = (
                await session.scalars(select(Incident).order_by(Incident.started_at.desc()).limit(10))
            ).all()

            summary = OverviewSummary(
                total=len(servers),
                online=sum(server.status == ServerStatus.ONLINE for server in servers),
                degraded=sum(server.status == ServerStatus.DEGRADED for server in servers),
                offline=sum(server.status == ServerStatus.OFFLINE for server in servers),
                unknown=sum(server.status == ServerStatus.UNKNOWN for server in servers),
            )

            return OverviewResponse(
                generated_at=datetime.now(timezone.utc),
                summary=summary,
                servers=cards,
                recent_incidents=[IncidentRead.model_validate(item) for item in incidents],
            )

    async def build_server_detail(self, server_id: int) -> ServerDetail | None:
        async with self.session_factory() as session:
            server = await session.scalar(
                select(Server)
                .options(selectinload(Server.service_checks))
                .where(Server.id == server_id)
            )
            if not server:
                return None

            history = await self._history(session, server_id, 96)
            latency_series = await self._metric_series(session, server_id, "avg_latency_ms", 72)
            packet_loss_series = await self._metric_series(session, server_id, "packet_loss", 72)
            incidents = (
                await session.scalars(
                    select(Incident).where(Incident.server_id == server_id).order_by(Incident.started_at.desc()).limit(10)
                )
            ).all()
            alerts = (
                await session.scalars(
                    select(AlertEvent).where(AlertEvent.server_id == server_id).order_by(AlertEvent.created_at.desc()).limit(10)
                )
            ).all()
            results = (
                await session.scalars(
                    select(CheckResult)
                    .where(CheckResult.server_id == server_id)
                    .order_by(CheckResult.checked_at.desc())
                    .limit(10)
                )
            ).all()

            card = await self._build_server_card(session, server)
            return ServerDetail(
                **card.model_dump(exclude={"history", "services"}),
                history=history,
                latency_series=latency_series,
                packet_loss_series=packet_loss_series,
                services=[service for service in server.service_checks],
                recent_incidents=[IncidentRead.model_validate(item) for item in incidents],
                recent_alerts=[AlertEventRead.model_validate(item) for item in alerts],
                latest_results=[CheckResultRead.model_validate(item) for item in results],
            )

    async def list_servers(self) -> list[ServerCard]:
        async with self.session_factory() as session:
            servers = (
                (
                    await session.scalars(
                        select(Server).options(selectinload(Server.service_checks)).order_by(Server.name.asc())
                    )
                )
                .unique()
                .all()
            )
            return [await self._build_server_card(session, server) for server in servers]

    async def list_incidents(self) -> list[IncidentRead]:
        async with self.session_factory() as session:
            incidents = (await session.scalars(select(Incident).order_by(desc(Incident.started_at)).limit(20))).all()
            return [IncidentRead.model_validate(item) for item in incidents]

    async def list_server_history(self, server_id: int, limit: int = 48) -> list[HistoryPoint]:
        async with self.session_factory() as session:
            return await self._history(session, server_id, limit)

    async def _build_server_card(self, session: AsyncSession, server: Server) -> ServerCard:
        history = await self._history(session, server.id, 48)
        return ServerCard(
            **server.__dict__,
            uptime_24h=await self._uptime(session, server.id, timedelta(hours=24)),
            uptime_7d=await self._uptime(session, server.id, timedelta(days=7)),
            uptime_30d=await self._uptime(session, server.id, timedelta(days=30)),
            history=history,
            services=[service for service in server.service_checks],
        )

    async def _history(self, session: AsyncSession, server_id: int, limit: int) -> list[HistoryPoint]:
        results = (
            await session.scalars(
                select(CheckResult)
                .where(CheckResult.server_id == server_id, CheckResult.service_check_id.is_(None))
                .order_by(CheckResult.checked_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            HistoryPoint(timestamp=result.checked_at, status=result.status, severity=result.severity)
            for result in reversed(results)
        ]

    async def _metric_series(
        self, session: AsyncSession, server_id: int, field_name: str, limit: int
    ) -> list[MetricPoint]:
        results = (
            await session.scalars(
                select(CheckResult)
                .where(CheckResult.server_id == server_id, CheckResult.service_check_id.is_(None))
                .order_by(CheckResult.checked_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            MetricPoint(timestamp=result.checked_at, value=getattr(result, field_name))
            for result in reversed(results)
        ]

    async def _uptime(self, session: AsyncSession, server_id: int, window: timedelta) -> float:
        started_at = datetime.now(timezone.utc) - window
        results = (
            await session.scalars(
                select(CheckResult.status).where(
                    CheckResult.server_id == server_id,
                    CheckResult.service_check_id.is_(None),
                    CheckResult.checked_at >= started_at,
                )
            )
        ).all()
        if not results:
            return 0.0
        available = sum(status != ServerStatus.OFFLINE for status in results)
        return round((available / len(results)) * 100, 2)
