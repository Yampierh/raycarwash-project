"""m_013 create provider_achievements

Auto-granted badges surfaced on the provider's public profile and in
their Profile Hub provider block. The `workers/achievement_evaluator.py`
cron (Phase 5 chunk Y6) inspects detailer state daily and inserts new
rows when criteria pass. Manual admin grants are also possible.

`achievement_type` is a String, NOT an enum — adding "ceramic_specialist"
or "fleet_pro" shouldn't need a migration. The (provider_user_id,
achievement_type) UNIQUE keeps the cron idempotent: a re-run for a
detailer that already earned `verified` is a no-op.

Revision ID: m_013
Revises: m_012
Create Date: 2026-05-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_013"
down_revision = "m_012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_achievements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("achievement_type", sa.String(60), nullable=False),
        # Free-form metadata captured at grant time (e.g. milestone
        # counts that triggered it). Kept as JSONB so the badge UI can
        # surface "Completed 100 jobs!" without joining other tables.
        sa.Column("metadata_", postgresql.JSONB, nullable=True),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "provider_user_id", "achievement_type",
            name="uq_provider_achievements_provider_type",
        ),
    )

    # Profile Hub block reads "what badges does this detailer have"
    # ordered newest-first to surface the latest grant.
    op.create_index(
        "idx_provider_achievements_provider_recent",
        "provider_achievements",
        ["provider_user_id", sa.text("awarded_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_provider_achievements_provider_recent",
        table_name="provider_achievements",
    )
    op.drop_table("provider_achievements")
