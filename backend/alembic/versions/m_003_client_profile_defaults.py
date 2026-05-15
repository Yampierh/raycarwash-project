"""m_003 client_profile defaults

Adds columns the Profile Hub `preferences` block consumes:

  default_vehicle_id          — pre-select in booking wizard
  default_address_id          — pre-fill service address (FK added in Phase 4
                                when user_addresses table lands; column here
                                is nullable UUID without FK)
  total_appointments_count    — denormalized via PostgreSQL trigger from
                                appointments status='completed' (Phase 9
                                m_020 adds the trigger; Phase 1 starts at 0)
  marketing_email_opt_in      — GDPR-grade opt-in
  frequency_preference        — "weekly"|"biweekly"|"monthly"|"custom"

`service_address` is left in place (deprecated) — Phase 4 migrates clients
to UserAddress.

Revision ID: m_003
Revises: m_002
Create Date: 2026-05-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_003"
down_revision = "m_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_profiles",
        sa.Column("default_vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # FK constraint targets vehicles.id; vehicles table exists in pre-Phase 0.
    op.create_foreign_key(
        "fk_client_profiles_default_vehicle_id",
        "client_profiles", "vehicles",
        ["default_vehicle_id"], ["id"],
        ondelete="SET NULL",
    )

    # user_addresses doesn't exist yet (Phase 4). Store the UUID without FK
    # for now; the constraint is added in m_010_link_client_profile_defaults.
    op.add_column(
        "client_profiles",
        sa.Column("default_address_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.add_column(
        "client_profiles",
        sa.Column(
            "total_appointments_count", sa.Integer(),
            nullable=False, server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "client_profiles",
        sa.Column(
            "total_spent_cents", sa.BigInteger(),
            nullable=False, server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "client_profiles",
        sa.Column(
            "marketing_email_opt_in", sa.Boolean(),
            nullable=False, server_default=sa.false(),
        ),
    )
    op.add_column(
        "client_profiles",
        sa.Column("frequency_preference", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client_profiles", "frequency_preference")
    op.drop_column("client_profiles", "marketing_email_opt_in")
    op.drop_column("client_profiles", "total_spent_cents")
    op.drop_column("client_profiles", "total_appointments_count")
    op.drop_column("client_profiles", "default_address_id")
    op.drop_constraint(
        "fk_client_profiles_default_vehicle_id",
        "client_profiles", type_="foreignkey",
    )
    op.drop_column("client_profiles", "default_vehicle_id")
