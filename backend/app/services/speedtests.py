from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.models import Server, SpeedTestResult, SpeedTestStatus
from backend.app.schemas.speed_test import AgentSpeedTestCompleteRequest


class SpeedTestService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

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

            await session.commit()
            await session.refresh(item)
            return item

    async def latest_for_server(self, server_id: int) -> SpeedTestResult | None:
        async with self.session_factory() as session:
            return await session.scalar(
                select(SpeedTestResult)
                .where(SpeedTestResult.server_id == server_id)
                .order_by(SpeedTestResult.created_at.desc())
            )

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
