"""m_024 cities table + provider signup multi-step columns

Plan 24 Wave 1 — schema base for the new auth pages (customer/provider
signup, staff login, admin dashboard multi-city support).

Two changes in one migration because they ship together:

  1. Create the `cities` lookup table (Plan 24 §5.2 A-1 + §3 P-2).
     Canonical list of markets RayCarWash operates in. `code` is the
     natural FK target (3-4 letter codes — fwa, ind, col, cin, lou).

  2. Add five columns to `provider_profiles` for the 7-step signup
     flow (Plan 24 §3):
       - ssn_last_4_encrypted   (P-1) Checkr identity verification
       - home_city_code         (P-2) market the detailer works in
       - water_tank_gallons     (P-3) equipment metadata
       - services_offered       (P-3) granular skill list (JSONB)
       - application_status     (P-7) lifecycle state machine

No FK from provider_profiles.home_city_code → cities.code. App-level
integrity is sufficient; FK would cascade on city retirement, which
we don't want.

Revision ID: m_024
Revises: m_023
Create Date: 2026-05-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_024"
down_revision = "m_023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cities table ──────────────────────────────────────────────────
    op.create_table(
        "cities",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(8), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False),
        sa.Column(
            "status", sa.String(16),
            nullable=False, server_default="pilot",
        ),
        sa.Column(
            "sort_order", sa.Integer(),
            nullable=False, server_default=sa.text("0"),
        ),
        # TimestampMixin
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "is_deleted", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("code", name="uq_cities_code"),
    )
    op.create_index(
        "ix_cities_status_sort", "cities", ["status", "sort_order"],
    )
    op.create_index("ix_cities_is_deleted", "cities", ["is_deleted"])

    # ── provider_profiles new columns ─────────────────────────────────
    op.add_column(
        "provider_profiles",
        sa.Column(
            "ssn_last_4_encrypted", sa.String(8), nullable=True,
            comment="Encrypted SSN last 4. Used once by Checkr; purge post-approval.",
        ),
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "home_city_code", sa.String(8), nullable=True,
            comment="Soft-reference to cities.code. App-level validation.",
        ),
    )
    op.create_index(
        "ix_provider_profiles_home_city_code",
        "provider_profiles",
        ["home_city_code"],
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "water_tank_gallons", sa.Integer(), nullable=True,
            comment="0 = use customer water; 20/40/60 = own tank size.",
        ),
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "services_offered", postgresql.JSONB(), nullable=True,
            comment="Skill list — e.g. ['soap','vacuum','polish','ceramic'].",
        ),
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "application_status", sa.String(20),
            nullable=False, server_default="draft",
            comment="Signup lifecycle: draft|submitted|bg_check_pending|docs_review|approved|rejected",
        ),
    )


def downgrade() -> None:
    op.drop_column("provider_profiles", "application_status")
    op.drop_column("provider_profiles", "services_offered")
    op.drop_column("provider_profiles", "water_tank_gallons")
    op.drop_index(
        "ix_provider_profiles_home_city_code",
        table_name="provider_profiles",
    )
    op.drop_column("provider_profiles", "home_city_code")
    op.drop_column("provider_profiles", "ssn_last_4_encrypted")

    op.drop_index("ix_cities_is_deleted", table_name="cities")
    op.drop_index("ix_cities_status_sort", table_name="cities")
    op.drop_table("cities")
