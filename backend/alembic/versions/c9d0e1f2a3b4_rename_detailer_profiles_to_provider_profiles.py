"""rename detailer_profiles to provider_profiles

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-04-25

Renames the detailer_profiles table and its associated constraints/indexes to
reflect the new ProviderProfile model name. The role value "detailer" in the
roles and user_roles tables is intentionally NOT renamed here because it is
embedded in live JWT tokens and renaming it would require invalidating all
existing sessions.

All application code now references the table as "provider_profiles"; old
migrations that reference "detailer_profiles" remain unchanged (they ran
before the rename and the history is immutable).
"""
from __future__ import annotations

from alembic import op

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename table
    op.rename_table("detailer_profiles", "provider_profiles")

    # Rename the primary key constraint (PostgreSQL auto-names it)
    op.execute(
        "ALTER TABLE provider_profiles "
        "RENAME CONSTRAINT detailer_profiles_pkey TO provider_profiles_pkey"
    )

    # Rename indexes — use IF EXISTS to tolerate naming variations
    op.execute(
        "ALTER INDEX IF EXISTS ix_detailer_profiles_user_id "
        "RENAME TO ix_provider_profiles_user_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_detailer_profiles_stripe_verification_session_id "
        "RENAME TO ix_provider_profiles_stripe_verification_session_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_detailer_profiles_is_deleted "
        "RENAME TO ix_provider_profiles_is_deleted"
    )

    # FK constraint on reviews.detailer_id → provider_profiles.id
    # PostgreSQL keeps FK names on the referencing table, not the referenced one.
    # The FK itself is valid regardless of the table name; no rename needed.


def downgrade() -> None:
    op.execute(
        "ALTER INDEX IF EXISTS ix_provider_profiles_is_deleted "
        "RENAME TO ix_detailer_profiles_is_deleted"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_provider_profiles_stripe_verification_session_id "
        "RENAME TO ix_detailer_profiles_stripe_verification_session_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_provider_profiles_user_id "
        "RENAME TO ix_detailer_profiles_user_id"
    )
    op.execute(
        "ALTER TABLE provider_profiles "
        "RENAME CONSTRAINT provider_profiles_pkey TO detailer_profiles_pkey"
    )
    op.rename_table("provider_profiles", "detailer_profiles")
