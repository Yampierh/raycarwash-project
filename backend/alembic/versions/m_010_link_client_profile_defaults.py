"""m_010 link client_profiles.default_address_id → user_addresses.id

m_003 added `client_profiles.default_address_id` as a nullable UUID
column WITHOUT an FK because `user_addresses` didn't exist yet. Now
that m_006 has shipped, add the constraint.

`default_vehicle_id` FK was already created in m_003 (vehicles existed
pre-Phase 0).

Revision ID: m_010
Revises: m_009
Create Date: 2026-05-15
"""
from __future__ import annotations

from alembic import op

revision = "m_010"
down_revision = "m_009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_client_profiles_default_address_id",
        "client_profiles", "user_addresses",
        ["default_address_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_client_profiles_default_address_id",
        "client_profiles",
        type_="foreignkey",
    )
