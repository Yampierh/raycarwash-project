"""add password_reset_tokens table and token_version to users

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-24

Changes:
  1. users.token_version (INTEGER, default 1, NOT NULL)
     - Enables instant session revocation: increment to invalidate all active JWTs
       without waiting for the 30-minute access token expiry window.
     - Backfills existing rows to 1.

  2. password_reset_tokens table (single-use DB-backed reset tokens)
     - Replaces stateless JWT reset tokens.
     - token_hash: SHA-256 of the raw token (raw token is never stored).
     - used_at: NULL while valid; set on first use — prevents replay attacks.
     - expires_at: 1-hour TTL enforced at application layer.
     - ix_password_reset_tokens_expires_at: index to support cleanup jobs.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Add token_version to users                                        #
    # ------------------------------------------------------------------ #
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Increment to instantly invalidate all active JWTs for this user.",
        ),
    )

    # ------------------------------------------------------------------ #
    # 2. Create password_reset_tokens table                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "token_hash",
            sa.String(64),
            nullable=False,
            unique=True,
            comment="SHA-256 hex digest of the raw reset token. Never store the raw token.",
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Set when token is consumed. NULL = still valid.",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_password_reset_tokens_expires_at",
        "password_reset_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "token_version")
