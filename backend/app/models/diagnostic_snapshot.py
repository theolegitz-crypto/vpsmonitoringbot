from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.enums import CheckType, ServerStatus, Severity


class DiagnosticSnapshot(Base):
    __tablename__ = "diagnostic_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_check_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_checks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(64), index=True)
    headline: Mapped[str] = mapped_column(String(255))
    check_type: Mapped[CheckType | None] = mapped_column(
        SqlEnum(CheckType, name="check_type"),
        nullable=True,
        index=True,
    )
    status: Mapped[ServerStatus | None] = mapped_column(
        SqlEnum(ServerStatus, name="server_status"),
        nullable=True,
        index=True,
    )
    severity: Mapped[Severity] = mapped_column(SqlEnum(Severity, name="severity_enum"), index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    server = relationship("Server", back_populates="diagnostic_snapshots")
    service_check = relationship("ServiceCheck")
