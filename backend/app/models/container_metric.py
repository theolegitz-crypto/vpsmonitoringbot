from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class ContainerMetric(Base):
    __tablename__ = "container_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    container_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    health_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    restart_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_usage_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_limit_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    server = relationship("Server", back_populates="container_metrics")
