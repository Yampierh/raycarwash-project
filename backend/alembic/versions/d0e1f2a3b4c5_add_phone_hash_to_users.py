"""add phone_hash column to users for O(1) phone lookup

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-04-25

Adds users.phone_hash — a SHA-256 hash of the normalized (E.164) phone number,
keyed with PHONE_LOOKUP_KEY.

Why: phone_number is stored encrypted with non-deterministic AES-CBC (random IV
per write). A WHERE clause on an encrypted column re-encrypts the search value
and always produces a different ciphertext from the stored one, so lookups always
return zero rows. The hash column enables O(1) index-based lookup without
decryption.

Security: HMAC with PHONE_LOOKUP_KEY prevents rainbow table attacks against the
hash column. The key is independent of ENCRYPTION_KEY and JWT_SECRET_KEY.

Existing rows: phone_hash is NULL for existing users. It is populated lazily
when a user sets or updates their phone number (security.update_user_phone_hash).
A backfill script is not included here because phone_number is encrypted and
cannot be read without application-level decryption — do a one-time backfill via
the admin API or a migration script that calls compute_phone_hash after decrypting.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "phone_hash",
            sa.String(64),
            nullable=True,
            comment="SHA-256(PHONE_LOOKUP_KEY + normalize(phone_number)). Enables O(1) phone lookup.",
        ),
    )
    op.create_index(
        "ix_users_phone_hash",
        "users",
        ["phone_hash"],
        unique=True,
        postgresql_where=sa.text("phone_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_phone_hash", table_name="users")
    op.drop_column("users", "phone_hash")
