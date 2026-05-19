import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.models import Server
from backend.app.schemas.agent import AgentIngestRequest, AgentIngestResponse
from backend.app.services.agent_ingest import AgentIngestService
from backend.app.services.ssh_remote import SshRemoteService


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SshCollectionResult:
    server_id: int
    server_name: str
    recorded_at: datetime
    containers_received: int


class SshMonitoringService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.agent_ingest_service = AgentIngestService(session_factory)
        self.remote = SshRemoteService()
        self._schedule_lock = asyncio.Lock()

    async def collect_server_metrics(self, server_id: int) -> SshCollectionResult:
        async with self.session_factory() as session:
            server = await session.get(Server, server_id)
            if not server:
                raise LookupError("Server not found")

            snapshot = await self.remote.collect_metrics(server)
            payload = AgentIngestRequest(
                server_id=server.id,
                agent_version="ssh-backend",
                collected_at=snapshot.recorded_at,
                metrics=snapshot.metrics,
                containers=snapshot.containers,
            )

        ingest_response = await self.agent_ingest_service.ingest(payload)

        async with self.session_factory() as session:
            server = await session.get(Server, server_id)
            if not server:
                raise LookupError("Server not found")
            server.last_ssh_metrics_at = ingest_response.recorded_at
            await session.commit()
            return SshCollectionResult(
                server_id=server.id,
                server_name=server.name,
                recorded_at=ingest_response.recorded_at,
                containers_received=ingest_response.containers_received,
            )

    async def run_due_collections(self) -> dict[str, int]:
        if self._schedule_lock.locked():
            return {"collected": 0, "failed": 0}

        async with self._schedule_lock:
            try:
                async with self.session_factory() as session:
                    servers = (
                        await session.scalars(
                            select(Server).where(
                                Server.ssh_enabled.is_(True),
                                Server.ssh_metrics_interval_seconds > 0,
                            )
                        )
                    ).all()
            except SQLAlchemyError as exc:
                logger.warning(
                    "SSH metrics scheduler skipped because database schema is not ready. Run Alembic migrations first. Details: %s",
                    exc,
                )
                return {"collected": 0, "failed": 0}

            now = datetime.now(timezone.utc)
            collected = 0
            failed = 0

            for server in servers:
                if not self._is_due(server.last_ssh_metrics_at, server.ssh_metrics_interval_seconds, now):
                    continue

                try:
                    await self.collect_server_metrics(server.id)
                    collected += 1
                except Exception as exc:
                    failed += 1
                    logger.warning("SSH metrics collection failed for %s: %s", server.name, exc)

            if collected:
                logger.info("Collected %s SSH metrics snapshot(s)", collected)
            return {"collected": collected, "failed": failed}

    @staticmethod
    def _is_due(last_collected_at: datetime | None, interval_seconds: int, now: datetime) -> bool:
        if interval_seconds <= 0:
            return False
        if last_collected_at is None:
            return True
        return last_collected_at <= now - timedelta(seconds=interval_seconds)
