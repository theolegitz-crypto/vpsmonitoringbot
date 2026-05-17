from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.enums import CheckType, ServerStatus


class ServiceCheck(Base):
    __tablename__ = "service_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    check_type: Mapped[CheckType] = mapped_column(SqlEnum(CheckType, name="check_type"), index=True)
    target: Mapped[str] = mapped_column(String(255))
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_status: Mapped[int] = mapped_column(Integer, default=200)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=5)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    ssl_expiry_warning_days: Mapped[int] = mapped_column(Integer, default=21)
    consecutive_alert_threshold: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[ServerStatus] = mapped_column(
        SqlEnum(ServerStatus, name="server_status"),
        default=ServerStatus.UNKNOWN,
        nullable=False,
        index=True,
    )
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_response_ms: Mapped[float | None] = mapped_column(nullable=True)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consecutive_issues: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    server = relationship("Server", back_populates="service_checks")
    check_results = relationship(
        "CheckResult", back_populates="service_check", cascade="all, delete-orphan"
    )
    incidents = relationship("Incident", back_populates="service_check", cascade="all, delete-orphan")
    alert_events = relationship("AlertEvent", back_populates="service_check", cascade="all, delete-orphan")
