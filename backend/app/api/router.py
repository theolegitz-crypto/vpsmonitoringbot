from fastapi import APIRouter, Depends

from backend.app.api.auth_deps import current_user
from backend.app.api.routes import auth, dashboard, health, servers
from backend.app.core.config import settings


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)

if settings.auth_enabled:
    protected_router = APIRouter(dependencies=[Depends(current_user)])
    protected_router.include_router(dashboard.router)
    protected_router.include_router(servers.router)
    api_router.include_router(protected_router)
else:
    api_router.include_router(dashboard.router)
    api_router.include_router(servers.router)
