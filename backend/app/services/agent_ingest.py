from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.models import AlertEvent, AgentMetric, ContainerMetric, DiagnosticSnapshot, Server, Severity
from backend.app.schemas.agent import AgentIngestRequest, AgentIngestResponse
from backend.app.services.notifier import TelegramNotifier


class AgentIngestService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.notifier = TelegramNotifier()

    async def ingest(self, payload: AgentIngestRequest) -> AgentIngestResponse:
        recorded_at = payload.collected_at or datetime.now(timezone.utc)

        async with self.session_factory() as session:
            server = await self._resolve_server(session, payload)
            if not server:
                raise LookupError("Server not found for agent payload")

            server.agent_last_seen_at = recorded_at
            server.agent_version = payload.agent_version

            session.add(
                AgentMetric(
                    server_id=server.id,
                    recorded_at=recorded_at,
                    **payload.metrics.model_dump(),
                )
            )

            for container in payload.containers:
                session.add(
                    ContainerMetric(
                        server_id=server.id,
                        recorded_at=recorded_at,
                        **container.model_dump(),
                    )
                )

            await self._emit_container_alerts(session, server, payload.containers, recorded_at)

            await session.commit()
            return AgentIngestResponse(
                server_id=server.id,
                containers_received=len(payload.containers),
                recorded_at=recorded_at,
            )

    async def _resolve_server(self, session: AsyncSession, payload: AgentIngestRequest) -> Server | None:
        if payload.server_id:
            return await session.get(Server, payload.server_id)
        return await session.scalar(select(Server).where(Server.name == payload.server_name))

    async def _emit_container_alerts(
        self,
        session: AsyncSession,
        server: Server,
        containers,
        recorded_at: datetime,
    ) -> None:
        muted = server.muted_until is not None and server.muted_until > recorded_at

        for container in containers:
            severity, event_type, message = self._classify_container_issue(server.name, container)
            if not message:
                continue

            recent_event = await session.scalar(
                select(AlertEvent)
                .where(
                    AlertEvent.server_id == server.id,
                    AlertEvent.event_type == event_type,
                    AlertEvent.message == message,
                    AlertEvent.created_at >= recorded_at - timedelta(minutes=30),
                )
                .order_by(desc(AlertEvent.created_at))
            )
            if recent_event:
                continue

            event = AlertEvent(
                server_id=server.id,
                severity=severity,
                event_type=event_type,
                message=message,
                sent_to_telegram=False,
            )
            session.add(event)

            session.add(
                DiagnosticSnapshot(
                    server_id=server.id,
                    category="container",
                    headline=message,
                    severity=severity,
                    details=container.model_dump(),
                    created_at=recorded_at,
                )
            )

            if not muted:
                event.sent_to_telegram = await self.notifier.send(message)

    @staticmethod
    def _classify_container_issue(server_name: str, container) -> tuple[Severity, str, str | None]:
        state = (container.state or "").lower()
        health = (container.health_status or "").lower()
        restarts = container.restart_count or 0
        label = f"{server_name}/{container.name}"

        if state and state not in {"running", "created"}:
            return Severity.CRITICAL, "container-down", f"Container {label} is {state}"

        if health in {"unhealthy", "failed"}:
            return Severity.CRITICAL, "container-unhealthy", f"Container {label} health is {health}"

        if restarts >= 3:
            return (
                Severity.WARNING,
                "container-crash-loop",
                f"Container {label} restarted {restarts} times",
            )

        return Severity.INFO, "container-ok", None
