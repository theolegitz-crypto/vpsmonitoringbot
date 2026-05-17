from fastapi import APIRouter

from backend.app.db.session import AsyncSessionLocal
from backend.app.schemas.common import IncidentRead
from backend.app.schemas.server import OverviewResponse
from backend.app.services.dashboard import DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])
dashboard_service = DashboardService(AsyncSessionLocal)


@router.get("/overview", response_model=OverviewResponse)
async def overview() -> OverviewResponse:
    return await dashboard_service.build_overview()


@router.get("/incidents", response_model=list[IncidentRead])
async def incidents() -> list[IncidentRead]:
    return await dashboard_service.list_incidents()

