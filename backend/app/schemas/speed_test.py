from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.models.enums import SpeedTestStatus


class SpeedTestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    status: SpeedTestStatus
    provider_name: str | None
    provider_location: str | None
    external_ip: str | None
    download_mbps: float | None
    upload_mbps: float | None
    ping_ms: float | None
    jitter_ms: float | None
    details: dict | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class SpeedTestQueueResponse(BaseModel):
    queued: bool
    speed_test: SpeedTestRead


class AgentSpeedTestClaimRequest(BaseModel):
    server_id: int | None = None
    server_name: str | None = None


class AgentSpeedTestCompleteRequest(BaseModel):
    status: SpeedTestStatus
    provider_name: str | None = None
    provider_location: str | None = None
    external_ip: str | None = None
    download_mbps: float | None = None
    upload_mbps: float | None = None
    ping_ms: float | None = None
    jitter_ms: float | None = None
    details: dict | None = None
    error: str | None = None
