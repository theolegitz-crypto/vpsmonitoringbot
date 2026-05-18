from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class AgentMetric(Base):
    __tablename__ = "agent_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_used_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_total_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    swap_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    swap_used_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    swap_total_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_used_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_total_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    load_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    load_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    load_15: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_rx_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    net_tx_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uptime_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    server = relationship("Server", back_populates="agent_metrics")
