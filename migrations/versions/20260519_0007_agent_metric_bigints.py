"""align agent metric counters to bigint

Revision ID: 20260519_0007
Revises: 20260519_0006
Create Date: 2026-05-19 11:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0007"
down_revision: Union[str, Sequence[str], None] = "20260519_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "agent_metrics",
        "net_rx_bytes",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        postgresql_using="net_rx_bytes::bigint",
        existing_nullable=True,
    )
    op.alter_column(
        "agent_metrics",
        "net_tx_bytes",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        postgresql_using="net_tx_bytes::bigint",
        existing_nullable=True,
    )
    op.alter_column(
        "agent_metrics",
        "uptime_seconds",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        postgresql_using="uptime_seconds::bigint",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "agent_metrics",
        "uptime_seconds",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        postgresql_using="uptime_seconds::integer",
        existing_nullable=True,
    )
    op.alter_column(
        "agent_metrics",
        "net_tx_bytes",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        postgresql_using="net_tx_bytes::integer",
        existing_nullable=True,
    )
    op.alter_column(
        "agent_metrics",
        "net_rx_bytes",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        postgresql_using="net_rx_bytes::integer",
        existing_nullable=True,
    )
