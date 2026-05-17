from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.enums import Severity


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_check_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_checks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    severity: Mapped[Severity] = mapped_column(SqlEnum(Severity, name="severity_enum"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    message: Mapped[str] = mapped_column(String(500))
    sent_to_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    server = relationship("Server", back_populates="alert_events")
    service_check = relationship("ServiceCheck", back_populates="alert_events")
