"""m_015 provider_profile: provider_type + is_active + composite unique

Integration plan E1.A (01-profiles.md). Adds the columns that turn
ProviderProfile from a 1:1 detailer-only model into a 1:N model keyed by
(user_id, provider_type). E1.A is intentionally aditivo:

  * provider_type column (default DETAILER, backfills existing rows)
  * is_active column (mirrors current is_accepting_bookings; the rename
    drop happens in E1.E once all call-sites read is_active)
  * drop the single-column unique on user_id and replace with
    composite unique on (user_id, provider_type)
  * partial index on (provider_type, is_active) for public listings

E1.A does NOT touch:
  - the relationship on User (still uselist=False) — E1.B flips it
  - detailer_services (renamed to provider_services in E1.D)
  - is_accepting_bookings column (still canonical until E1.E)

The unique constraint name from the original column-level `unique=True`
predates the rename from detailer_profiles. Both possible names are
dropped IF EXISTS for cross-environment safety.

Revision ID: m_015
Revises: m_014
Create Date: 2026-05-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m_015"
down_revision = "m_014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Add provider_type with default DETAILER so existing rows backfill
    #    safely. NOT NULL is fine because the server_default fills every row.
    op.add_column(
        "provider_profiles",
        sa.Column(
            "provider_type",
            sa.String(20),
            nullable=False,
            server_default="detailer",
        ),
    )

    # 2) Add is_active mirroring is_accepting_bookings. E1.E drops the
    #    old column.
    op.add_column(
        "provider_profiles",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    # Backfill is_active from is_accepting_bookings so existing detailers
    # that had paused themselves stay paused.
    op.execute(
        "UPDATE provider_profiles SET is_active = is_accepting_bookings"
    )

    # 3) Drop the single-column unique on user_id. The constraint may have
    #    been named differently depending on when the table was renamed
    #    from detailer_profiles, so try both known forms with IF EXISTS.
    op.execute(
        "ALTER TABLE provider_profiles "
        "DROP CONSTRAINT IF EXISTS provider_profiles_user_id_key"
    )
    op.execute(
        "ALTER TABLE provider_profiles "
        "DROP CONSTRAINT IF EXISTS detailer_profiles_user_id_key"
    )

    # 4) Composite unique replaces it. Now a user can hold one DETAILER
    #    AND one MECHANIC profile but not two of the same type.
    op.create_unique_constraint(
        "uq_provider_profiles_user_type",
        "provider_profiles",
        ["user_id", "provider_type"],
    )

    # 5) Helper index for public listings filtered by vertical + active flag.
    op.create_index(
        "ix_provider_profiles_type_active",
        "provider_profiles",
        ["provider_type", "is_active"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_profiles_type_active",
        table_name="provider_profiles",
    )
    op.drop_constraint(
        "uq_provider_profiles_user_type",
        "provider_profiles",
        type_="unique",
    )
    # Restore single-column unique. Postgres auto-names it
    # provider_profiles_user_id_key; we name it explicitly for symmetry.
    op.create_unique_constraint(
        "provider_profiles_user_id_key",
        "provider_profiles",
        ["user_id"],
    )
    op.drop_column("provider_profiles", "is_active")
    op.drop_column("provider_profiles", "provider_type")
