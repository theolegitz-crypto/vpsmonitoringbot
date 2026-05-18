"""add agent metrics, diagnostics, and rollups

Revision ID: 20260518_0003
Revises: 20260517_0002
Create Date: 2026-05-18 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260518_0003"
down_revision: Union[str, Sequence[str], None] = "20260517_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


server_status = postgresql.ENUM(
    "ONLINE", "DEGRADED", "OFFLINE", "UNKNOWN", name="server_status", create_type=False
)
severity_enum = postgresql.ENUM(
    "INFO", "WARNING", "CRITICAL", name="severity_enum", create_type=False
)
check_type = postgresql.ENUM(
    "ICMP", "HTTP", "TCP", "SSL", name="check_type", create_type=False
)


def upgrade() -> None:
    op.add_column("servers", sa.Column("agent_last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("servers", sa.Column("agent_version", sa.String(length=64), nullable=True))

    op.create_table(
        "agent_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("memory_percent", sa.Float(), nullable=True),
        sa.Column("memory_used_mb", sa.Float(), nullable=True),
        sa.Column("memory_total_mb", sa.Float(), nullable=True),
        sa.Column("swap_percent", sa.Float(), nullable=True),
        sa.Column("swap_used_mb", sa.Float(), nullable=True),
        sa.Column("swap_total_mb", sa.Float(), nullable=True),
        sa.Column("disk_percent", sa.Float(), nullable=True),
        sa.Column("disk_used_gb", sa.Float(), nullable=True),
        sa.Column("disk_total_gb", sa.Float(), nullable=True),
        sa.Column("load_1", sa.Float(), nullable=True),
        sa.Column("load_5", sa.Float(), nullable=True),
        sa.Column("load_15", sa.Float(), nullable=True),
        sa.Column("net_rx_bytes", sa.BigInteger(), nullable=True),
        sa.Column("net_tx_bytes", sa.BigInteger(), nullable=True),
        sa.Column("uptime_seconds", sa.BigInteger(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_agent_metrics_server_id", "agent_metrics", ["server_id"])
    op.create_index("ix_agent_metrics_recorded_at", "agent_metrics", ["recorded_at"])

    op.create_table(
        "container_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("container_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("health_status", sa.String(length=64), nullable=True),
        sa.Column("restart_count", sa.Integer(), nullable=True),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("memory_usage_mb", sa.Float(), nullable=True),
        sa.Column("memory_limit_mb", sa.Float(), nullable=True),
        sa.Column("memory_percent", sa.Float(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_container_metrics_server_id", "container_metrics", ["server_id"])
    op.create_index("ix_container_metrics_container_id", "container_metrics", ["container_id"])
    op.create_index("ix_container_metrics_name", "container_metrics", ["name"])
    op.create_index("ix_container_metrics_health_status", "container_metrics", ["health_status"])
    op.create_index("ix_container_metrics_recorded_at", "container_metrics", ["recorded_at"])

    op.create_table(
        "diagnostic_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=True),
        sa.Column(
            "service_check_id",
            sa.Integer(),
            sa.ForeignKey("service_checks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=False),
        sa.Column("check_type", check_type, nullable=True),
        sa.Column("status", server_status, nullable=True),
        sa.Column("severity", severity_enum, nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_diagnostic_snapshots_server_id", "diagnostic_snapshots", ["server_id"])
    op.create_index("ix_diagnostic_snapshots_service_check_id", "diagnostic_snapshots", ["service_check_id"])
    op.create_index("ix_diagnostic_snapshots_category", "diagnostic_snapshots", ["category"])
    op.create_index("ix_diagnostic_snapshots_check_type", "diagnostic_snapshots", ["check_type"])
    op.create_index("ix_diagnostic_snapshots_status", "diagnostic_snapshots", ["status"])
    op.create_index("ix_diagnostic_snapshots_severity", "diagnostic_snapshots", ["severity"])
    op.create_index("ix_diagnostic_snapshots_created_at", "diagnostic_snapshots", ["created_at"])

    op.create_table(
        "check_result_rollups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=True),
        sa.Column(
            "service_check_id",
            sa.Integer(),
            sa.ForeignKey("service_checks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("check_type", check_type, nullable=False),
        sa.Column("bucket_date", sa.Date(), nullable=False),
        sa.Column("total_checks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("online_checks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("degraded_checks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offline_checks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unknown_checks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("avg_packet_loss", sa.Float(), nullable=True),
        sa.Column("avg_response_time_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_check_result_rollups_server_id", "check_result_rollups", ["server_id"])
    op.create_index("ix_check_result_rollups_service_check_id", "check_result_rollups", ["service_check_id"])
    op.create_index("ix_check_result_rollups_check_type", "check_result_rollups", ["check_type"])
    op.create_index("ix_check_result_rollups_bucket_date", "check_result_rollups", ["bucket_date"])


def downgrade() -> None:
    op.drop_table("check_result_rollups")
    op.drop_table("diagnostic_snapshots")
    op.drop_table("container_metrics")
    op.drop_table("agent_metrics")
    op.drop_column("servers", "agent_version")
    op.drop_column("servers", "agent_last_seen_at")
