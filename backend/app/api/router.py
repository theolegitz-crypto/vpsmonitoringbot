from fastapi import APIRouter

from backend.app.api.routes import dashboard, health, servers


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(servers.router)

