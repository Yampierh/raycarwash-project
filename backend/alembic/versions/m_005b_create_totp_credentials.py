"""m_005b create totp_credentials

One row per user, gates `auth/two-fa/*` endpoints. The TOTP secret is
encrypted at rest (Fernet via EncryptedType in the model — same key as
User PII). Backup codes are stored as one-way hashes; a list of plain
codes is shown ONCE during enrollment and never persisted.

The `enabled` flag is False between `/two-fa/enroll` (which writes the
row) and `/two-fa/verify` (which flips the bit after the user confirms
the first OTP from their authenticator app).

Revision ID: m_005b
Revises: m_005
Create Date: 2026-05-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_005b"
down_revision = "m_005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "totp_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,  # one TOTP per user
        ),
        sa.Column("secret_encrypted", sa.String(255), nullable=False),
        # Backup codes: list of one-way hashes. The plain codes are
        # returned exactly once during enrollment and re-generation.
        sa.Column(
            "backup_codes_hashes",
            postgresql.ARRAY(sa.String(64)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("totp_credentials")
