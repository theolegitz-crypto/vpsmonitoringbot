from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.models.enums import CheckType, IncidentStatus, ServerStatus, Severity


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float | None


class HistoryPoint(BaseModel):
    timestamp: datetime
    status: ServerStatus
    severity: Severity


class IncidentRead(ORMModel):
    id: int
    server_id: int | None
    service_check_id: int | None
    severity: Severity
    title: str
    description: str
    status: IncidentStatus
    started_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None


class AlertEventRead(ORMModel):
    id: int
    server_id: int | None
    service_check_id: int | None
    severity: Severity
    event_type: str
    message: str
    sent_to_telegram: bool
    created_at: datetime


class CheckResultRead(ORMModel):
    id: int
    server_id: int | None
    service_check_id: int | None
    check_type: CheckType
    status: ServerStatus
    severity: Severity
    avg_latency_ms: float | None
    min_latency_ms: float | None
    max_latency_ms: float | None
    jitter_ms: float | None
    packet_loss: float | None
    response_time_ms: float | None
    status_code: int | None
    message: str | None
    checked_at: datetime


class DiagnosticSnapshotRead(ORMModel):
    id: int
    server_id: int | None
    service_check_id: int | None
    category: str
    headline: str
    check_type: CheckType | None
    status: ServerStatus | None
    severity: Severity
    details: dict | None
    created_at: datetime
