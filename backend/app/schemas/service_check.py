from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.models.enums import CheckType, ServerStatus


class ServiceCheckBase(BaseModel):
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


class ServiceCheckCreate(ServiceCheckBase):
    pass


class ServiceCheckUpdate(BaseModel):
    name: str | None = None
    target: str | None = None
    port: int | None = None
    path: str | None = None
    expected_status: int | None = None
    timeout_seconds: int | None = None
    interval_seconds: int | None = None
    ssl_expiry_warning_days: int | None = None
    consecutive_alert_threshold: int | None = None
    muted_until: datetime | None = None


class ServiceCheckRead(ServiceCheckBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    status: ServerStatus
    muted_until: datetime | None
    last_check_at: datetime | None
    last_response_ms: float | None
    last_status_code: int | None
    last_error: str | None
    consecutive_issues: int
    consecutive_alert_threshold: int
    created_at: datetime
    updated_at: datetime | None
