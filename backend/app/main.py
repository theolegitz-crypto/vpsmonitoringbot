from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.services.auth import AuthService
from backend.app.tasks.scheduler import MonitoringScheduler


scheduler = MonitoringScheduler()
auth_service = AuthService(AsyncSessionLocal)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auth_enabled:
        await auth_service.ensure_bootstrap_admin()
    if settings.scheduler_enabled:
        await scheduler.start()
    yield
    if settings.scheduler_enabled:
        await scheduler.stop()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)
