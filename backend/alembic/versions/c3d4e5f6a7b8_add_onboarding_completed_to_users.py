"""add onboarding_completed to users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-24

Adds onboarding_completed boolean to users table.
This is the single source of truth for whether a user has completed
the registration onboarding flow (selected role + provided full_name).

Backfill: existing users with at least one role are marked as completed.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )

    # Backfill: users who already have at least one role are considered complete
    op.execute(
        """
        UPDATE users u
        SET onboarding_completed = TRUE
        WHERE EXISTS (
            SELECT 1 FROM user_role_associations ura
            WHERE ura.user_id = u.id
        )
        """
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
