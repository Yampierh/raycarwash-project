"""m_005 create pending_contact_changes

Holds the in-flight state of an email or phone change request. The new
value is NOT applied to `users` until the user proves they control the
new contact (click the email link / type the SMS OTP). Per ADR-001
anti-takeover + plan §6.4:

  - new_value_encrypted   PII at rest (Fernet via EncryptedType)
  - new_value_hash        deterministic HMAC for uniqueness/lookup
  - verification_token_hash  one-way hash of the token mailed/SMSed
  - attempts              OTP-only — caps at 5 then locks the row
  - expires_at            1h for email, 10 min for phone
  - consumed_at           soft-delete; row is kept for audit

`workers/pending_contact_cleanup.py` (Phase 3 chunk P, RQ scheduled hourly)
deletes rows with `expires_at < now()` AND no consumed_at.

Revision ID: m_005
Revises: m_004
Create Date: 2026-05-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_005"
down_revision = "m_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_contact_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # "email" | "phone" — small enum, stored as String to avoid the
        # PG ENUM bookkeeping that other Profile entities don't need.
        sa.Column("change_type", sa.String(10), nullable=False),
        sa.Column("new_value_encrypted", sa.String(255), nullable=False),
        sa.Column("new_value_hash", sa.String(64), nullable=False),
        sa.Column("verification_token_hash", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Lookup by token during confirm: O(1) on the hash, never on the raw token.
    op.create_index(
        "idx_pending_contact_token",
        "pending_contact_changes",
        ["verification_token_hash"],
        unique=False,
    )
    # Cleanup worker scans by expiry.
    op.create_index(
        "idx_pending_contact_expires",
        "pending_contact_changes",
        ["expires_at"],
    )
    # Per-user lookup (rate limit checks, "your pending change").
    op.create_index(
        "idx_pending_contact_user_type",
        "pending_contact_changes",
        ["user_id", "change_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_pending_contact_user_type", table_name="pending_contact_changes")
    op.drop_index("idx_pending_contact_expires", table_name="pending_contact_changes")
    op.drop_index("idx_pending_contact_token", table_name="pending_contact_changes")
    op.drop_table("pending_contact_changes")
