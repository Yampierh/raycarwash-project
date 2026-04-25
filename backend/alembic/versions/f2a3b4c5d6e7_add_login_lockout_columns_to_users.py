"""add failed_login_attempts and locked_until to users for account lockout

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-25

Adds brute-force protection to the users table.

failed_login_attempts: INTEGER NOT NULL DEFAULT 0
  Incremented on each consecutive failed password login.
  Reset to 0 on successful authentication.

locked_until: TIMESTAMPTZ NULL
  Set to NOW() + 15 minutes when failed_login_attempts reaches 5.
  While locked_until is in the future, password login is rejected.
  Self-expires: once the timestamp passes, login is allowed again and
  the counter resets on the next successful login.

Logic lives in AuthService.authenticate_user() (app/services/auth.py).
Threshold and window are class-level constants (_LOCKOUT_THRESHOLD=5,
_LOCKOUT_MINUTES=15) — change in code, not DB, if tuning is needed.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Consecutive failed password login attempts since last success.",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="If set and in the future, password login is rejected.",
        ),
    )
    # Sparse index: only users that are currently locked (a tiny minority)
    op.create_index(
        "ix_users_locked_until",
        "users",
        ["locked_until"],
        postgresql_where=sa.text("locked_until IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_locked_until", table_name="users")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
