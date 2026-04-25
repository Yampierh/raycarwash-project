"""migrate provider specialties from JSONB to junction table

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-04-25

Replaces provider_profiles.specialties (JSONB list of strings) with a proper
relational model:

  specialties           — lookup table of named specialty types
  provider_specialties  — junction table (provider_profile_id, specialty_id)

Benefits:
  - Efficient filtering via JOIN (previously required JSONB @> operator with
    no standard B-tree index support)
  - Referential integrity — no dangling slug strings in free-form arrays
  - Future: per-specialty pricing, category grouping, i18n names

Steps:
  1. CREATE TABLE specialties (seed with known slugs)
  2. CREATE TABLE provider_specialties
  3. Backfill junction rows from JSONB array via lateral join
  4. DROP COLUMN provider_profiles.specialties
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None

# Canonical specialty slugs — the full set referenced in detailer_seed.py
# plus common additions. Add new slugs here; they require no schema migration.
_SPECIALTIES = [
    ("ceramic_coating",       "Ceramic Coating"),
    ("paint_correction",      "Paint Correction"),
    ("full_detail",           "Full Detail"),
    ("interior_detail",       "Interior Detail"),
    ("exterior_wash",         "Exterior Wash"),
    ("engine_bay",            "Engine Bay Cleaning"),
    ("paint_decontamination", "Paint Decontamination"),
    ("window_tinting",        "Window Tinting"),
    ("luxury_vehicles",       "Luxury Vehicles"),
    ("trucks",                "Trucks & SUVs"),
    ("fleet",                 "Fleet Services"),
    ("express_wash",          "Express Wash"),
    ("eco_friendly",          "Eco-Friendly Products"),
    ("budget_friendly",       "Budget-Friendly"),
    ("family_vehicles",       "Family Vehicles"),
    ("exterior",              "Exterior Detail"),
    ("bilingual",             "Bilingual Service"),
    ("mobile_mechanic",       "Mobile Mechanic"),
]


def upgrade() -> None:
    # ---- 1. Create specialties lookup table ----
    op.create_table(
        "specialties",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("slug",        sa.String(50),  nullable=False, unique=True),
        sa.Column("name",        sa.String(100), nullable=False),
        sa.Column("description", sa.Text,        nullable=True),
    )
    op.create_index("ix_specialties_slug", "specialties", ["slug"])

    # Seed the lookup table
    conn = op.get_bind()
    for slug, name in _SPECIALTIES:
        conn.execute(
            sa.text(
                "INSERT INTO specialties (id, slug, name) VALUES (:id, :slug, :name)"
                " ON CONFLICT (slug) DO NOTHING"
            ),
            {"id": str(uuid.uuid4()), "slug": slug, "name": name},
        )

    # ---- 2. Create junction table ----
    op.create_table(
        "provider_specialties",
        sa.Column(
            "provider_profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "specialty_id",
            UUID(as_uuid=True),
            sa.ForeignKey("specialties.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ---- 3. Backfill junction rows from JSONB ----
    conn.execute(sa.text("""
        INSERT INTO provider_specialties (provider_profile_id, specialty_id, added_at)
        SELECT
            pp.id                  AS provider_profile_id,
            s.id                   AS specialty_id,
            NOW()                  AS added_at
        FROM provider_profiles pp
        CROSS JOIN LATERAL jsonb_array_elements_text(
            COALESCE(pp.specialties, '[]'::jsonb)
        ) AS elem(slug)
        JOIN specialties s ON s.slug = elem.slug
        WHERE pp.specialties IS NOT NULL
          AND pp.specialties != 'null'::jsonb
          AND jsonb_array_length(pp.specialties) > 0
        ON CONFLICT DO NOTHING
    """))

    # ---- 4. Drop the JSONB column ----
    op.drop_column("provider_profiles", "specialties")


def downgrade() -> None:
    # Restore JSONB column and backfill from junction table
    op.add_column(
        "provider_profiles",
        sa.Column(
            "specialties",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            comment='List of specialty tags (restored from junction table on downgrade).',
        ),
    )
    op.get_bind().execute(sa.text("""
        UPDATE provider_profiles pp
        SET specialties = (
            SELECT jsonb_agg(s.slug ORDER BY s.slug)
            FROM provider_specialties ps
            JOIN specialties s ON s.id = ps.specialty_id
            WHERE ps.provider_profile_id = pp.id
        )
    """))

    op.drop_table("provider_specialties")
    op.drop_index("ix_specialties_slug", table_name="specialties")
    op.drop_table("specialties")
