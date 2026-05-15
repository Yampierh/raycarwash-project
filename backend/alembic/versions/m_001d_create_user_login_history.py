"""m_001d create user_login_history

Records every login attempt (successful and failed) for the `/auth/history`
endpoint, suspicious-activity detection, and the security_summary block of
the Profile Hub.

Retention is enforced by `workers/login_history_purger.py` (12 months for
successes, 90 days for failures).

Revision ID: m_001d
Revises: m_001c
Create Date: 2026-05-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_001d"
down_revision = "m_001c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_login_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "login_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("ip_location", sa.String(120), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("device_name", sa.String(80), nullable=True),
        sa.Column("auth_method", sa.String(20), nullable=False),
        sa.Column("was_successful", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("failure_reason", sa.String(60), nullable=True),
        sa.Column("refresh_token_family_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Hot path: list user's login history newest-first
    op.create_index(
        "idx_login_history_user_time",
        "user_login_history",
        ["user_id", sa.text("login_at DESC")],
    )
    # Brute-force / failed-attempt analytics
    op.create_index(
        "idx_login_history_failed",
        "user_login_history",
        ["user_id", "was_successful", sa.text("login_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_login_history_failed", table_name="user_login_history")
    op.drop_index("idx_login_history_user_time", table_name="user_login_history")
    op.drop_table("user_login_history")
