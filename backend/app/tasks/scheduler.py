import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.app.core.config import settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.services.monitoring import MonitoringService


class MonitoringScheduler:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.monitoring_service = MonitoringService(AsyncSessionLocal)

    async def start(self) -> None:
        self.scheduler.add_job(
            self.monitoring_service.run_due_checks,
            trigger="interval",
            seconds=settings.scheduler_tick_seconds,
            id="due-checks",
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.start()
        if settings.run_initial_checks:
            asyncio.create_task(self.monitoring_service.run_due_checks())

    async def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

