"""m_016 rename detailer_services -> provider_services + m2m categories

Integration plan E1.D (01-profiles.md §2.3 + §2.4). Two related refactors
folded into one migration because they target the same data plane and
the schema would otherwise lag the model in between:

  A. Rename `detailer_services` table to `provider_services` and column
     `detailer_id` -> `provider_id`. Also renames the composite unique
     and the index so a fresh `\\d provider_services` matches the new
     vocabulary.
  B. Replace the scalar `provider_profiles.service_category_id` with a
     proper m2m junction `provider_service_categories(provider_id,
     category_id)`. Detailer/mechanic profiles can now offer multiple
     service categories — e.g. a detailer that covers basic_wash +
     interior_detail + full_detail simultaneously.

Data preservation:
  - Existing detailer_services rows survive intact (CASCADE FKs follow
    the rename).
  - service_category_id values backfill into the junction table, then
    the scalar column drops.

Downgrade picks the first category per provider (alphabetical) to
restore the scalar column. Providers with multiple categories lose all
but one — acceptable for a forward-only refactor.

Revision ID: m_016
Revises: m_015
Create Date: 2026-05-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "m_016"
down_revision = "m_015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── A. Rename detailer_services → provider_services ────────────────────

    # Drop the old composite unique first (its name references the legacy
    # vocabulary).
    op.drop_constraint(
        "uq_detailer_service",
        "detailer_services",
        type_="unique",
    )

    # Drop the (auto-named) index on detailer_id so the column rename
    # doesn't trip over a stale index name. Postgres auto-names column
    # indexes `<table>_<col>_idx`; we use IF EXISTS to tolerate any
    # name drift from prior environments.
    op.execute(
        "DROP INDEX IF EXISTS ix_detailer_services_detailer_id"
    )

    # Rename the column.
    op.alter_column(
        "detailer_services",
        "detailer_id",
        new_column_name="provider_id",
    )

    # Rename the table.
    op.rename_table("detailer_services", "provider_services")

    # Recreate the index and unique under the new names.
    op.create_index(
        "ix_provider_services_provider_id",
        "provider_services",
        ["provider_id"],
    )
    op.create_unique_constraint(
        "uq_provider_service",
        "provider_services",
        ["provider_id", "service_id"],
    )

    # ── B. m2m provider_service_categories ─────────────────────────────────

    op.create_table(
        "provider_service_categories",
        sa.Column(
            "provider_id",
            UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            UUID(as_uuid=True),
            sa.ForeignKey("service_categories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Backfill from the scalar column. Use INSERT ... ON CONFLICT to
    # tolerate a re-run on partial data.
    op.execute("""
        INSERT INTO provider_service_categories (provider_id, category_id, added_at)
        SELECT id, service_category_id, NOW()
        FROM provider_profiles
        WHERE service_category_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)

    # Drop the now-redundant scalar column. Its FK constraint goes with it.
    op.drop_column("provider_profiles", "service_category_id")


def downgrade() -> None:
    # ── B. Restore scalar service_category_id from junction ────────────────
    op.add_column(
        "provider_profiles",
        sa.Column(
            "service_category_id",
            UUID(as_uuid=True),
            sa.ForeignKey("service_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Pick the first category per provider (alphabetical by category id)
    # to populate the scalar column. Providers with multiple categories
    # keep only one — downgrade is best-effort.
    op.execute("""
        UPDATE provider_profiles pp
        SET service_category_id = (
            SELECT psc.category_id
            FROM provider_service_categories psc
            WHERE psc.provider_id = pp.id
            ORDER BY psc.category_id::text ASC
            LIMIT 1
        )
    """)
    op.create_index(
        "ix_provider_profiles_service_category_id",
        "provider_profiles",
        ["service_category_id"],
    )
    op.drop_table("provider_service_categories")

    # ── A. Reverse the rename ──────────────────────────────────────────────
    op.drop_constraint(
        "uq_provider_service",
        "provider_services",
        type_="unique",
    )
    op.drop_index(
        "ix_provider_services_provider_id",
        table_name="provider_services",
    )
    op.rename_table("provider_services", "detailer_services")
    op.alter_column(
        "detailer_services",
        "provider_id",
        new_column_name="detailer_id",
    )
    op.create_index(
        "ix_detailer_services_detailer_id",
        "detailer_services",
        ["detailer_id"],
    )
    op.create_unique_constraint(
        "uq_detailer_service",
        "detailer_services",
        ["detailer_id", "service_id"],
    )
