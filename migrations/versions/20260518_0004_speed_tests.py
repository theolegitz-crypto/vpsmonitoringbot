"""add speed test queue and results

Revision ID: 20260518_0004
Revises: 20260518_0003
Create Date: 2026-05-18 01:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260518_0004"
down_revision: Union[str, Sequence[str], None] = "20260518_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


speed_test_status = postgresql.ENUM(
    "PENDING", "RUNNING", "COMPLETED", "FAILED", name="speed_test_status", create_type=False
)
speed_test_status_create = postgresql.ENUM(
    "PENDING", "RUNNING", "COMPLETED", "FAILED", name="speed_test_status"
)


def upgrade() -> None:
    bind = op.get_bind()
    speed_test_status_create.create(bind, checkfirst=True)

    op.create_table(
        "speed_test_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", speed_test_status, nullable=False, server_default="PENDING"),
        sa.Column("provider_name", sa.String(length=255), nullable=True),
        sa.Column("provider_location", sa.String(length=255), nullable=True),
        sa.Column("external_ip", sa.String(length=64), nullable=True),
        sa.Column("download_mbps", sa.Float(), nullable=True),
        sa.Column("upload_mbps", sa.Float(), nullable=True),
        sa.Column("ping_ms", sa.Float(), nullable=True),
        sa.Column("jitter_ms", sa.Float(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_speed_test_results_server_id", "speed_test_results", ["server_id"])
    op.create_index("ix_speed_test_results_status", "speed_test_results", ["status"])
    op.create_index("ix_speed_test_results_created_at", "speed_test_results", ["created_at"])


def downgrade() -> None:
    op.drop_table("speed_test_results")
    bind = op.get_bind()
    speed_test_status_create.drop(bind, checkfirst=True)
