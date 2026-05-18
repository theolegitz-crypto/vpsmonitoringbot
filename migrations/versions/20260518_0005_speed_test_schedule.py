"""add regular speed test scheduling fields to servers

Revision ID: 20260518_0005
Revises: 20260518_0004
Create Date: 2026-05-18 06:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260518_0005"
down_revision: Union[str, Sequence[str], None] = "20260518_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "servers",
        sa.Column("speed_test_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "servers",
        sa.Column("speed_test_interval_seconds", sa.Integer(), nullable=False, server_default=sa.text("21600")),
    )
    op.add_column(
        "servers",
        sa.Column("last_speed_test_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("servers", "speed_test_enabled", server_default=None)
    op.alter_column("servers", "speed_test_interval_seconds", server_default=None)


def downgrade() -> None:
    op.drop_column("servers", "last_speed_test_requested_at")
    op.drop_column("servers", "speed_test_interval_seconds")
    op.drop_column("servers", "speed_test_enabled")
