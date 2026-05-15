"""m_001b add users.last_step_up_at for step-up DB fallback (ADR-004)

When Redis is unavailable, `require_step_up()` falls back to this column.
Updated by `AuthService.mark_step_up()` on every successful auth event.

Revision ID: m_001b
Revises: m_001
Create Date: 2026-05-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m_001b"
down_revision = "m_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "last_step_up_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last successful auth event timestamp (UTC). DB fallback for Redis step-up cache.",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "last_step_up_at")
