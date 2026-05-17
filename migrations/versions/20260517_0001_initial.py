"""initial monitoring schema

Revision ID: 20260517_0001
Revises:
Create Date: 2026-05-17 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260517_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


server_status = postgresql.ENUM(
    "ONLINE", "DEGRADED", "OFFLINE", "UNKNOWN", name="server_status", create_type=False
)
severity_enum = postgresql.ENUM(
    "INFO", "WARNING", "CRITICAL", name="severity_enum", create_type=False
)
incident_status = postgresql.ENUM(
    "OPEN", "RESOLVED", name="incident_status", create_type=False
)
check_type = postgresql.ENUM(
    "ICMP", "HTTP", "TCP", "SSL", name="check_type", create_type=False
)

server_status_create = postgresql.ENUM(
    "ONLINE", "DEGRADED", "OFFLINE", "UNKNOWN", name="server_status"
)
severity_enum_create = postgresql.ENUM(
    "INFO", "WARNING", "CRITICAL", name="severity_enum"
)
incident_status_create = postgresql.ENUM(
    "OPEN", "RESOLVED", name="incident_status"
)
check_type_create = postgresql.ENUM(
    "ICMP", "HTTP", "TCP", "SSL", name="check_type"
)


def upgrade() -> None:
    bind = op.get_bind()
    server_status_create.create(bind, checkfirst=True)
    severity_enum_create.create(bind, checkfirst=True)
    incident_status_create.create(bind, checkfirst=True)
    check_type_create.create(bind, checkfirst=True)

    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", server_status, nullable=False, server_default="UNKNOWN"),
        sa.Column("latency_warning_ms", sa.Float(), nullable=False, server_default="150"),
        sa.Column("latency_critical_ms", sa.Float(), nullable=False, server_default="400"),
        sa.Column("packet_loss_warning", sa.Float(), nullable=False, server_default="5"),
        sa.Column("packet_loss_critical", sa.Float(), nullable=False, server_default="20"),
        sa.Column("check_interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("consecutive_alert_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_latency_ms", sa.Float(), nullable=True),
        sa.Column("last_packet_loss", sa.Float(), nullable=True),
        sa.Column("last_jitter_ms", sa.Float(), nullable=True),
        sa.Column("consecutive_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("name", name="uq_servers_name"),
    )
    op.create_index("ix_servers_name", "servers", ["name"])
    op.create_index("ix_servers_address", "servers", ["address"])
    op.create_index("ix_servers_status", "servers", ["status"])

    op.create_table(
        "service_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("check_type", check_type, nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("expected_status", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("ssl_expiry_warning_days", sa.Integer(), nullable=False, server_default="21"),
        sa.Column("consecutive_alert_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("status", server_status, nullable=False, server_default="UNKNOWN"),
        sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_response_ms", sa.Float(), nullable=True),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.String(length=255), nullable=True),
        sa.Column("consecutive_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_service_checks_server_id", "service_checks", ["server_id"])
    op.create_index("ix_service_checks_check_type", "service_checks", ["check_type"])
    op.create_index("ix_service_checks_status", "service_checks", ["status"])

    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("service_check_id", sa.Integer(), sa.ForeignKey("service_checks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("check_type", check_type, nullable=False),
        sa.Column("status", server_status, nullable=False),
        sa.Column("severity", severity_enum, nullable=False),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("min_latency_ms", sa.Float(), nullable=True),
        sa.Column("max_latency_ms", sa.Float(), nullable=True),
        sa.Column("jitter_ms", sa.Float(), nullable=True),
        sa.Column("packet_loss", sa.Float(), nullable=True),
        sa.Column("response_time_ms", sa.Float(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_check_results_server_id", "check_results", ["server_id"])
    op.create_index("ix_check_results_service_check_id", "check_results", ["service_check_id"])
    op.create_index("ix_check_results_checked_at", "check_results", ["checked_at"])

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("service_check_id", sa.Integer(), sa.ForeignKey("service_checks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("severity", severity_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", incident_status, nullable=False, server_default="OPEN"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_incidents_server_id", "incidents", ["server_id"])
    op.create_index("ix_incidents_service_check_id", "incidents", ["service_check_id"])
    op.create_index("ix_incidents_status", "incidents", ["status"])

    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("service_check_id", sa.Integer(), sa.ForeignKey("service_checks.id", ondelete="CASCADE"), nullable=True),
        sa.Column("severity", severity_enum, nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("sent_to_telegram", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_alert_events_server_id", "alert_events", ["server_id"])
    op.create_index("ix_alert_events_service_check_id", "alert_events", ["service_check_id"])
    op.create_index("ix_alert_events_created_at", "alert_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("alert_events")
    op.drop_table("incidents")
    op.drop_table("check_results")
    op.drop_table("service_checks")
    op.drop_table("servers")

    bind = op.get_bind()
    check_type_create.drop(bind, checkfirst=True)
    incident_status_create.drop(bind, checkfirst=True)
    severity_enum_create.drop(bind, checkfirst=True)
    server_status_create.drop(bind, checkfirst=True)
