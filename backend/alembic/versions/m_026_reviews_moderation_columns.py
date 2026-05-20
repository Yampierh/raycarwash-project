"""m_026 reviews moderation columns

Plan 24 W2-D — admin reviews moderation queue.

Adds four columns to `reviews` to power the moderation queue + approve/hide
endpoints. We deliberately do NOT introduce a `review_flags` table at this
stage: auto-flag rules are static (rating ≤ 2 or profanity keyword match)
and computed at query time, so flag history is implicit in the review row
itself. If we later need user-reported flags or per-rule audit, we can add
the table as a follow-up.

Columns:
  - moderation_state: "auto_pending" | "approved" | "hidden"
    Default "auto_pending" so newly-created reviews enter the queue; the
    queue endpoint filters auto_pending rows that match a flag rule.
  - moderation_actor_id: admin user who resolved the review (NULL until
    the queue is acted on).
  - moderation_acted_at: timestamp of the moderation decision.
  - moderation_note: optional free-text rationale (e.g. why hidden).

We also backfill existing rows to "approved" so they don't appear in the
queue retroactively — they pre-date the moderation system.

Revision ID: m_026
Revises: m_025
Create Date: 2026-05-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_026"
down_revision = "m_025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column(
            "moderation_state", sa.String(16),
            nullable=False, server_default="auto_pending",
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "moderation_actor_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "moderation_acted_at", sa.DateTime(timezone=True), nullable=True,
        ),
    )
    op.add_column(
        "reviews",
        sa.Column("moderation_note", sa.Text(), nullable=True),
    )

    # Backfill: existing reviews pre-date moderation. Mark them approved
    # so the queue doesn't surface historical content.
    op.execute(
        "UPDATE reviews SET moderation_state = 'approved' "
        "WHERE moderation_state = 'auto_pending'"
    )

    op.create_check_constraint(
        "ck_reviews_moderation_state",
        "reviews",
        "moderation_state IN ('auto_pending', 'approved', 'hidden')",
    )

    # Partial index — only auto_pending rows hit the queue endpoint.
    op.create_index(
        "ix_reviews_moderation_pending",
        "reviews",
        ["created_at"],
        postgresql_where=sa.text("moderation_state = 'auto_pending'"),
    )


def downgrade() -> None:
    op.drop_index("ix_reviews_moderation_pending", table_name="reviews")
    op.drop_constraint("ck_reviews_moderation_state", "reviews", type_="check")
    op.drop_column("reviews", "moderation_note")
    op.drop_column("reviews", "moderation_acted_at")
    op.drop_column("reviews", "moderation_actor_id")
    op.drop_column("reviews", "moderation_state")
