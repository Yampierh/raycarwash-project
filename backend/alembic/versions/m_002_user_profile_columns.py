"""m_002 user profile columns

Adds columns the Profile Hub needs on `users`:

  avatar_s3_key       — key returned by FileStorageAdapter, URL signed on read
  cover_s3_key        — cover image (detailers only by convention)
  pronouns            — UX-inclusive optional label
  preferred_language  — IETF BCP-47 tag, default "en"
  preferred_timezone  — IANA tz, default America/Indiana/Indianapolis
  last_active_at      — used by privacy show_last_active and admin filters
  active_role         — currently-selected role for dual-role users (echoed
                        into the JWT role claim by AuthService._build_token)

`is_deleted` + `deleted_at` already exist on TimestampMixin, so no GDPR
columns are added here.

Revision ID: m_002
Revises: m_001d
Create Date: 2026-05-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m_002"
down_revision = "m_001d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_s3_key", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("cover_s3_key", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("pronouns", sa.String(20), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "preferred_language", sa.String(10), nullable=False,
            server_default=sa.text("'en'"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "preferred_timezone", sa.String(64), nullable=False,
            server_default=sa.text("'America/Indiana/Indianapolis'"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("active_role", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "active_role")
    op.drop_column("users", "last_active_at")
    op.drop_column("users", "preferred_timezone")
    op.drop_column("users", "preferred_language")
    op.drop_column("users", "pronouns")
    op.drop_column("users", "cover_s3_key")
    op.drop_column("users", "avatar_s3_key")
