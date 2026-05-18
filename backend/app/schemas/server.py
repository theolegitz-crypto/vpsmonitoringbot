from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import CheckType, ServerStatus
from backend.app.schemas.agent import AgentMetricRead, ContainerMetricRead
from backend.app.schemas.common import (
    AlertEventRead,
    CheckResultRead,
    DiagnosticSnapshotRead,
    HistoryPoint,
    IncidentRead,
    MetricPoint,
)
from backend.app.schemas.speed_test import SpeedTestRead
from backend.app.schemas.service_check import ServiceCheckRead


class ServerBase(BaseModel):
    name: str
    address: str
    description: str | None = None
    latency_warning_ms: float = 150.0
    latency_critical_ms: float = 400.0
    packet_loss_warning: float = 5.0
    packet_loss_critical: float = 20.0
    check_interval_seconds: int = 60
    consecutive_alert_threshold: int = 3


class ServerCreate(ServerBase):
    service_checks: list["ServiceCheckPayload"] = Field(default_factory=list)


class ServerUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    description: str | None = None
    latency_warning_ms: float | None = None
    latency_critical_ms: float | None = None
    packet_loss_warning: float | None = None
    packet_loss_critical: float | None = None
    check_interval_seconds: int | None = None
    consecutive_alert_threshold: int | None = None
    muted_until: datetime | None = None


class ServiceCheckPayload(BaseModel):
    name: str
    check_type: CheckType
    target: str
    port: int | None = None
    path: str | None = None
    expected_status: int = 200
    timeout_seconds: int = 5
    interval_seconds: int = 60
    ssl_expiry_warning_days: int = 21
    consecutive_alert_threshold: int = 3


class UptimeWindow(BaseModel):
    label: str
    uptime_percent: float


class ServerRead(ServerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ServerStatus
    muted_until: datetime | None
    last_check_at: datetime | None
    last_latency_ms: float | None
    last_packet_loss: float | None
    last_jitter_ms: float | None
    agent_last_seen_at: datetime | None
    agent_version: str | None
    consecutive_issues: int
    created_at: datetime
    updated_at: datetime | None


class ServerCard(ServerRead):
    uptime_24h: float
    uptime_7d: float
    uptime_30d: float
    history: list[HistoryPoint]
    services: list[ServiceCheckRead]


class ServerDetail(ServerRead):
    uptime_24h: float
    uptime_7d: float
    uptime_30d: float
    history: list[HistoryPoint]
    latency_series: list[MetricPoint]
    packet_loss_series: list[MetricPoint]
    services: list[ServiceCheckRead]
    recent_incidents: list[IncidentRead]
    recent_alerts: list[AlertEventRead]
    latest_results: list[CheckResultRead]
    latest_agent_metric: AgentMetricRead | None = None
    current_containers: list[ContainerMetricRead] = Field(default_factory=list)
    recent_diagnostics: list[DiagnosticSnapshotRead] = Field(default_factory=list)
    latest_speed_test: SpeedTestRead | None = None


class OverviewSummary(BaseModel):
    total: int
    online: int
    degraded: int
    offline: int
    unknown: int


class OverviewResponse(BaseModel):
    generated_at: datetime
    summary: OverviewSummary
    servers: list[ServerCard]
    recent_incidents: list[IncidentRead]


class MuteRequest(BaseModel):
    duration: str
