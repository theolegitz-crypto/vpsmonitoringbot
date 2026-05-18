from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from backend.app.models import (
    AgentMetric,
    AlertEvent,
    CheckResult,
    ContainerMetric,
    DiagnosticSnapshot,
    Incident,
    Server,
    ServerStatus,
    SpeedTestResult,
)
from backend.app.schemas.agent import AgentMetricRead, ContainerMetricRead
from backend.app.schemas.common import (
    AlertEventRead,
    CheckResultRead,
    DiagnosticSnapshotRead,
    HistoryPoint,
    IncidentRead,
    MetricPoint,
)
from backend.app.schemas.server import OverviewResponse, OverviewSummary, ServerCard, ServerDetail
from backend.app.schemas.speed_test import SpeedTestRead
from backend.app.schemas.service_check import ServiceCheckRead


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
            latest_agent_metric = await session.scalar(
                select(AgentMetric)
                .where(AgentMetric.server_id == server_id)
                .order_by(AgentMetric.recorded_at.desc())
            )
            latest_container_timestamp = await session.scalar(
                select(ContainerMetric.recorded_at)
                .where(ContainerMetric.server_id == server_id)
                .order_by(ContainerMetric.recorded_at.desc())
            )
            current_containers = []
            if latest_container_timestamp:
                current_containers = (
                    await session.scalars(
                        select(ContainerMetric)
                        .where(
                            ContainerMetric.server_id == server_id,
                            ContainerMetric.recorded_at == latest_container_timestamp,
                        )
                        .order_by(ContainerMetric.name.asc())
                    )
                ).all()
            recent_diagnostics = (
                await session.scalars(
                    select(DiagnosticSnapshot)
                    .where(DiagnosticSnapshot.server_id == server_id)
                    .order_by(DiagnosticSnapshot.created_at.desc())
                    .limit(12)
                )
            ).all()
            latest_speed_test = await session.scalar(
                select(SpeedTestResult)
                .where(SpeedTestResult.server_id == server_id)
                .order_by(SpeedTestResult.created_at.desc())
            )

            card = await self._build_server_card(session, server)
            return ServerDetail(
                **card.model_dump(exclude={"history", "services"}),
                history=history,
                latency_series=latency_series,
                packet_loss_series=packet_loss_series,
                services=card.services,
                recent_incidents=[IncidentRead.model_validate(item) for item in incidents],
                recent_alerts=[AlertEventRead.model_validate(item) for item in alerts],
                latest_results=[CheckResultRead.model_validate(item) for item in results],
                latest_agent_metric=(
                    AgentMetricRead.model_validate(latest_agent_metric) if latest_agent_metric else None
                ),
                current_containers=[
                    ContainerMetricRead.model_validate(item) for item in current_containers
                ],
                recent_diagnostics=[
                    DiagnosticSnapshotRead.model_validate(item) for item in recent_diagnostics
                ],
                latest_speed_test=(
                    SpeedTestRead.model_validate(latest_speed_test) if latest_speed_test else None
                ),
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
        services = [await self._build_service_check_read(session, service) for service in server.service_checks]
        return ServerCard(
            **server.__dict__,
            uptime_24h=await self._uptime(session, server.id, timedelta(hours=24)),
            uptime_7d=await self._uptime(session, server.id, timedelta(days=7)),
            uptime_30d=await self._uptime(session, server.id, timedelta(days=30)),
            history=history,
            services=services,
        )

    async def _build_service_check_read(
        self, session: AsyncSession, service_check
    ) -> ServiceCheckRead:
        history = await self._service_history(session, service_check.id, 48)
        return ServiceCheckRead(
            **service_check.__dict__,
            uptime_24h=await self._service_uptime(session, service_check.id, timedelta(hours=24)),
            uptime_7d=await self._service_uptime(session, service_check.id, timedelta(days=7)),
            uptime_30d=await self._service_uptime(session, service_check.id, timedelta(days=30)),
            history=history,
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

    async def _service_history(
        self, session: AsyncSession, service_check_id: int, limit: int
    ) -> list[HistoryPoint]:
        results = (
            await session.scalars(
                select(CheckResult)
                .where(CheckResult.service_check_id == service_check_id)
                .order_by(CheckResult.checked_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            HistoryPoint(timestamp=result.checked_at, status=result.status, severity=result.severity)
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

    async def _service_uptime(
        self, session: AsyncSession, service_check_id: int, window: timedelta
    ) -> float:
        started_at = datetime.now(timezone.utc) - window
        results = (
            await session.scalars(
                select(CheckResult.status).where(
                    CheckResult.service_check_id == service_check_id,
                    CheckResult.checked_at >= started_at,
                )
            )
        ).all()
        if not results:
            return 0.0
        available = sum(status != ServerStatus.OFFLINE for status in results)
        return round((available / len(results)) * 100, 2)
