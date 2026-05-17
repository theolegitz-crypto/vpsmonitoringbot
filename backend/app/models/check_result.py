from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.enums import CheckType, ServerStatus, Severity


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_check_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_checks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    check_type: Mapped[CheckType] = mapped_column(SqlEnum(CheckType, name="check_type"), index=True)
    status: Mapped[ServerStatus] = mapped_column(SqlEnum(ServerStatus, name="server_status"), index=True)
    severity: Mapped[Severity] = mapped_column(SqlEnum(Severity, name="severity_enum"), index=True)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    jitter_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    server = relationship("Server", back_populates="check_results")
    service_check = relationship("ServiceCheck", back_populates="check_results")
