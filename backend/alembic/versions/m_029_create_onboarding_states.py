"""m_029 create onboarding_states table for FSM orchestration

Creates the core persistence layer for the OnboardingService state
machine. Each user gets exactly one row (unique user_id) that tracks
their progress through the signup flow.

Revision ID: m_029
Revises: m_028
Create Date: 2026-05-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_029"
down_revision = "m_028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, unique=True, index=True,
        ),
        sa.Column("status", sa.String(30), nullable=False,
                  server_default="pending_registration"),
        sa.Column("current_step", sa.String(50), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("completed", sa.Boolean, nullable=False,
                  server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean, nullable=False,
                  server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("onboarding_states")
