"""m_006 create user_addresses

Backs the `addresses` block of the Profile Hub and supersedes the
legacy `ClientProfile.service_address` single string. Users can register
multiple labelled addresses (Home, Work, secondary) with denormalized
lat/lng + H3 r9 so the booking flow + matching engine read them without
re-geocoding.

The geocoded coordinates come from the GeocodingAdapter (Nominatim in
dev, Google Maps in prod — selected in app/core/dependencies.py).

Revision ID: m_006
Revises: m_005b
Create Date: 2026-05-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_006"
down_revision = "m_005b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(40), nullable=True),  # "Home", "Work", custom
        sa.Column("line1", sa.String(200), nullable=False),
        sa.Column("line2", sa.String(200), nullable=True),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("state", sa.String(60), nullable=False),
        sa.Column("zip_code", sa.String(20), nullable=False),
        sa.Column("country", sa.String(60), nullable=False, server_default=sa.text("'US'")),
        # Geocoded denormalization — Numeric(9,6) gives ~10 cm precision.
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("h3_index_r9", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),  # "Gate code 1234", parking hints
        sa.Column(
            "is_default",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Per-user listing — newest first.
    op.create_index(
        "idx_user_addresses_user_active",
        "user_addresses",
        ["user_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # At most one default per user (partial unique). Mirrors the
    # convention used for payment_methods (m_007) and vehicles defaults.
    op.create_index(
        "idx_user_addresses_default_unique",
        "user_addresses",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true AND is_deleted = false"),
    )

    # H3 lookup for matching engine ("addresses near hex r9 = ?").
    op.create_index(
        "idx_user_addresses_h3",
        "user_addresses",
        ["h3_index_r9"],
        postgresql_where=sa.text("h3_index_r9 IS NOT NULL AND is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("idx_user_addresses_h3", table_name="user_addresses")
    op.drop_index("idx_user_addresses_default_unique", table_name="user_addresses")
    op.drop_index("idx_user_addresses_user_active", table_name="user_addresses")
    op.drop_table("user_addresses")
