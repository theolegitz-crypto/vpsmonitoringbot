from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentMetricPayload(BaseModel):
    cpu_percent: float | None = None
    memory_percent: float | None = None
    memory_used_mb: float | None = None
    memory_total_mb: float | None = None
    swap_percent: float | None = None
    swap_used_mb: float | None = None
    swap_total_mb: float | None = None
    disk_percent: float | None = None
    disk_used_gb: float | None = None
    disk_total_gb: float | None = None
    load_1: float | None = None
    load_5: float | None = None
    load_15: float | None = None
    net_rx_bytes: int | None = None
    net_tx_bytes: int | None = None
    uptime_seconds: int | None = None
    details: dict = Field(default_factory=dict)


class ContainerMetricPayload(BaseModel):
    container_id: str
    name: str
    image: str | None = None
    state: str | None = None
    status: str | None = None
    health_status: str | None = None
    restart_count: int | None = None
    cpu_percent: float | None = None
    memory_usage_mb: float | None = None
    memory_limit_mb: float | None = None
    memory_percent: float | None = None
    details: dict = Field(default_factory=dict)


class AgentIngestRequest(BaseModel):
    server_id: int | None = None
    server_name: str | None = None
    agent_version: str | None = None
    collected_at: datetime | None = None
    metrics: AgentMetricPayload
    containers: list[ContainerMetricPayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_server_target(self):
        if not self.server_id and not self.server_name:
            raise ValueError("Either server_id or server_name must be provided")
        return self


class AgentIngestResponse(BaseModel):
    accepted: bool = True
    server_id: int
    containers_received: int
    recorded_at: datetime


class AgentMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cpu_percent: float | None
    memory_percent: float | None
    memory_used_mb: float | None
    memory_total_mb: float | None
    swap_percent: float | None
    swap_used_mb: float | None
    swap_total_mb: float | None
    disk_percent: float | None
    disk_used_gb: float | None
    disk_total_gb: float | None
    load_1: float | None
    load_5: float | None
    load_15: float | None
    net_rx_bytes: int | None
    net_tx_bytes: int | None
    uptime_seconds: int | None
    details: dict | None
    recorded_at: datetime


class ContainerMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    container_id: str
    name: str
    image: str | None
    state: str | None
    status: str | None
    health_status: str | None
    restart_count: int | None
    cpu_percent: float | None
    memory_usage_mb: float | None
    memory_limit_mb: float | None
    memory_percent: float | None
    details: dict | None
    recorded_at: datetime
