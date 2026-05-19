"""add cancelled speed test status

Revision ID: 20260519_0008
Revises: 20260519_0007
Create Date: 2026-05-19 22:10:00
"""

from alembic import op


revision = "20260519_0008"
down_revision = "20260519_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE speed_test_status ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade() -> None:
    # PostgreSQL enum value removal is intentionally omitted.
    pass
