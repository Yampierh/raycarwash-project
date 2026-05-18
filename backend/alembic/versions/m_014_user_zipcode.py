"""m_014 user.zip_code

Integration plan E0 (00-user.md): a coarse location hint captured at
signup. Not a replacement for UserAddress — purely a low-friction onboarding
field used by matching heuristics to bias default search radius and surface
local providers before the user has typed a full address.

Indexed because future matching cohorts may filter users by zip prefix.

Revision ID: m_014
Revises: m_013
Create Date: 2026-05-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m_014"
down_revision = "m_013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("zip_code", sa.String(10), nullable=True),
    )
    op.create_index(
        "ix_users_zip_code",
        "users",
        ["zip_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_users_zip_code", table_name="users")
    op.drop_column("users", "zip_code")
