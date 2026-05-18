from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.enums import SpeedTestStatus


class SpeedTestResult(Base):
    __tablename__ = "speed_test_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    status: Mapped[SpeedTestStatus] = mapped_column(
        SqlEnum(SpeedTestStatus, name="speed_test_status"),
        default=SpeedTestStatus.PENDING,
        nullable=False,
        index=True,
    )
    provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    download_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    ping_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    jitter_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    server = relationship("Server", back_populates="speed_test_results")
