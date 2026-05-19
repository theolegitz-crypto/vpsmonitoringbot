from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.enums import ServerStatus


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    address: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ServerStatus] = mapped_column(
        SqlEnum(ServerStatus, name="server_status"),
        default=ServerStatus.UNKNOWN,
        nullable=False,
        index=True,
    )
    latency_warning_ms: Mapped[float] = mapped_column(Float, default=150.0)
    latency_critical_ms: Mapped[float] = mapped_column(Float, default=400.0)
    packet_loss_warning: Mapped[float] = mapped_column(Float, default=5.0)
    packet_loss_critical: Mapped[float] = mapped_column(Float, default=20.0)
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    consecutive_alert_threshold: Mapped[int] = mapped_column(Integer, default=3)
    ssh_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ssh_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22)
    ssh_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ssh_password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    ssh_metrics_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    ssh_collect_docker: Mapped[bool] = mapped_column(Boolean, default=True)
    last_ssh_metrics_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    speed_test_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    speed_test_interval_seconds: Mapped[int] = mapped_column(Integer, default=21600)
    last_speed_test_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_packet_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_jitter_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    agent_last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    consecutive_issues: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    service_checks = relationship(
        "ServiceCheck", back_populates="server", cascade="all, delete-orphan"
    )
    check_results = relationship("CheckResult", back_populates="server", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="server", cascade="all, delete-orphan")
    alert_events = relationship("AlertEvent", back_populates="server", cascade="all, delete-orphan")
    agent_metrics = relationship("AgentMetric", back_populates="server", cascade="all, delete-orphan")
    container_metrics = relationship("ContainerMetric", back_populates="server", cascade="all, delete-orphan")
    diagnostic_snapshots = relationship(
        "DiagnosticSnapshot", back_populates="server", cascade="all, delete-orphan"
    )
    speed_test_results = relationship(
        "SpeedTestResult", back_populates="server", cascade="all, delete-orphan"
    )

    @property
    def ssh_password_configured(self) -> bool:
        return bool(self.ssh_password_encrypted)
