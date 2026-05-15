"""m_001 extend audit_actions enum for Profile system

Adds the new AuditAction values needed across Profile phases:
profile/security/contact/payment/document/provider/role/notification/privacy/
account-deletion/data-export.

Action is stored as String(50), not a native PostgreSQL enum, so this migration
is a no-op at the DB level — the change is purely in Python. We still record
the migration to preserve a linear history.

Revision ID: m_001
Revises: b4c5d6e7f8a9
Create Date: 2026-05-14
"""
from __future__ import annotations

from alembic import op  # noqa: F401

revision = "m_001"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AuditAction is a Python enum stored as String — no schema change required.
    # New values: PROFILE_UPDATED, AVATAR_CHANGED, COVER_CHANGED,
    # EMAIL_CHANGE_REQUESTED, EMAIL_CHANGED, PHONE_CHANGE_REQUESTED, PHONE_CHANGED,
    # PASSWORD_CHANGED, TWO_FA_ENABLED, TWO_FA_DISABLED, PASSKEY_REGISTERED,
    # PASSKEY_REVOKED, SESSION_REVOKED, ALL_SESSIONS_REVOKED, PAYMENT_METHOD_*,
    # ADDRESS_*, VEHICLE_*, FAVORITE_*, DOCUMENT_*, PROVIDER_MODE_*,
    # PROVIDER_PROFILE_UPDATED, PROVIDER_STATUS_CHANGED, ROLE_SWITCHED,
    # NOTIFICATION_PREFS_UPDATED, PRIVACY_SETTINGS_UPDATED,
    # DATA_EXPORT_REQUESTED, DATA_EXPORT_READY,
    # ACCOUNT_DELETION_REQUESTED, ACCOUNT_DELETION_CANCELLED, ACCOUNT_ANONYMIZED.
    pass


def downgrade() -> None:
    # No-op: removing enum values from Python is not destructive to existing
    # rows in audit_logs (action is just a string). Old action strings remain
    # readable by older code as opaque values.
    pass
