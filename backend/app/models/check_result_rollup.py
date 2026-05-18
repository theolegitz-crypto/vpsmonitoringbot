from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.enums import CheckType


class CheckResultRollup(Base):
    __tablename__ = "check_result_rollups"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_check_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_checks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    check_type: Mapped[CheckType] = mapped_column(SqlEnum(CheckType, name="check_type"), index=True)
    bucket_date: Mapped[date] = mapped_column(Date, index=True)
    total_checks: Mapped[int] = mapped_column(Integer, default=0)
    online_checks: Mapped[int] = mapped_column(Integer, default=0)
    degraded_checks: Mapped[int] = mapped_column(Integer, default=0)
    offline_checks: Mapped[int] = mapped_column(Integer, default=0)
    unknown_checks: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_packet_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    server = relationship("Server")
    service_check = relationship("ServiceCheck")
