from fastapi import APIRouter, Header, HTTPException, status

from backend.app.core.config import settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.schemas.agent import AgentIngestRequest, AgentIngestResponse
from backend.app.schemas.speed_test import (
    AgentSpeedTestClaimRequest,
    AgentSpeedTestCompleteRequest,
    SpeedTestRead,
)
from backend.app.services.agent_ingest import AgentIngestService
from backend.app.services.speedtests import SpeedTestService


router = APIRouter(prefix="/agent", tags=["agent"])
agent_ingest_service = AgentIngestService(AsyncSessionLocal)
speed_test_service = SpeedTestService(AsyncSessionLocal)


def _require_agent_token(x_agent_token: str | None) -> None:
    if not settings.agent_ingest_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent ingest is disabled")
    if not settings.agent_shared_token or x_agent_token != settings.agent_shared_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token")


@router.post("/ingest", response_model=AgentIngestResponse)
async def ingest_agent(
    payload: AgentIngestRequest,
    x_agent_token: str | None = Header(default=None),
) -> AgentIngestResponse:
    _require_agent_token(x_agent_token)
    try:
        return await agent_ingest_service.ingest(payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/speed-tests/claim", response_model=SpeedTestRead | None)
async def claim_speed_test(
    payload: AgentSpeedTestClaimRequest,
    x_agent_token: str | None = Header(default=None),
) -> SpeedTestRead | None:
    _require_agent_token(x_agent_token)
    try:
        task = await speed_test_service.claim_next(payload.server_id, payload.server_name)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if not task:
        return None
    return SpeedTestRead.model_validate(task)


@router.post("/speed-tests/{speed_test_id}/complete", response_model=SpeedTestRead)
async def complete_speed_test(
    speed_test_id: int,
    payload: AgentSpeedTestCompleteRequest,
    x_agent_token: str | None = Header(default=None),
) -> SpeedTestRead:
    _require_agent_token(x_agent_token)
    try:
        task = await speed_test_service.complete(speed_test_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SpeedTestRead.model_validate(task)
