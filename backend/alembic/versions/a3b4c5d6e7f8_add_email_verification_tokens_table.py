"""add email_verification_tokens table

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-05-11

Changes:
  email_verification_tokens table — DB-backed stateful email verification tokens.
  Replaces stateless JWT approach so tokens can be invalidated and are single-use.

  Columns:
    id UUID PK
    user_id UUID FK → users.id ON DELETE CASCADE
    token_hash VARCHAR(64) UNIQUE — SHA-256 of the raw token (raw never stored)
    used_at TIMESTAMP nullable — set on first use; prevents replay
    expires_at TIMESTAMP NOT NULL — 24h TTL enforced at application layer
    created_at TIMESTAMP NOT NULL

  Indexes:
    ix_email_verification_tokens_user_id — fast lookup by user
    ix_email_verification_tokens_expires_at — cleanup worker filter
    uq_email_verification_tokens_token_hash — uniqueness constraint
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_email_verification_tokens_expires_at",
        "email_verification_tokens",
        ["expires_at"],
    )
    op.create_unique_constraint(
        "uq_email_verification_tokens_token_hash",
        "email_verification_tokens",
        ["token_hash"],
    )


def downgrade() -> None:
    op.drop_table("email_verification_tokens")
