"""m_008 create client_favorites

Backs the `favorites` block of the Profile Hub. A client can pin
providers they've worked with before so the Hub can surface them as
quick re-book options and `stats.favorite_provider_id` (denormalized
follow-up — Phase 9) can pick one without scanning appointments.

Revision ID: m_008
Revises: m_007
Create Date: 2026-05-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_008"
down_revision = "m_007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_favorites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Idempotency — re-favoring the same provider is a no-op, not a duplicate.
        sa.UniqueConstraint(
            "user_id", "provider_user_id",
            name="uq_client_favorites_pair",
        ),
    )

    # Per-user listing for `/users/me/favorites/providers`.
    op.create_index(
        "idx_client_favorites_user_recent",
        "client_favorites",
        ["user_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_client_favorites_user_recent", table_name="client_favorites")
    op.drop_table("client_favorites")
