"""add SSH monitoring fields to servers

Revision ID: 20260519_0006
Revises: 20260518_0005
Create Date: 2026-05-19 09:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0006"
down_revision: Union[str, Sequence[str], None] = "20260518_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "servers",
        sa.Column("ssh_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("servers", sa.Column("ssh_host", sa.String(length=255), nullable=True))
    op.add_column(
        "servers",
        sa.Column("ssh_port", sa.Integer(), nullable=False, server_default=sa.text("22")),
    )
    op.add_column("servers", sa.Column("ssh_username", sa.String(length=128), nullable=True))
    op.add_column("servers", sa.Column("ssh_password_encrypted", sa.Text(), nullable=True))
    op.add_column(
        "servers",
        sa.Column(
            "ssh_metrics_interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("300"),
        ),
    )
    op.add_column(
        "servers",
        sa.Column("ssh_collect_docker", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "servers",
        sa.Column("last_ssh_metrics_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.alter_column("servers", "ssh_enabled", server_default=None)
    op.alter_column("servers", "ssh_port", server_default=None)
    op.alter_column("servers", "ssh_metrics_interval_seconds", server_default=None)
    op.alter_column("servers", "ssh_collect_docker", server_default=None)


def downgrade() -> None:
    op.drop_column("servers", "last_ssh_metrics_at")
    op.drop_column("servers", "ssh_collect_docker")
    op.drop_column("servers", "ssh_metrics_interval_seconds")
    op.drop_column("servers", "ssh_password_encrypted")
    op.drop_column("servers", "ssh_username")
    op.drop_column("servers", "ssh_port")
    op.drop_column("servers", "ssh_host")
    op.drop_column("servers", "ssh_enabled")
