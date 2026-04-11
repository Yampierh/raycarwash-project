"""add arrived status and arrived_at column

Revision ID: a1b2c3d4e5f6
Revises: 860f2d1f8752
Create Date: 2026-04-11

Adds:
  - 'arrived' value to appointment_status_enum PostgreSQL enum type
  - arrived_at column on appointments table
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "860f2d1f8752"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL requires ADD VALUE to run outside a transaction for PG < 12.
    # PG 12+ allows it inside transactions, but the safest cross-version approach
    # is to use IF NOT EXISTS (available since PG 9.3).
    op.execute(
        "ALTER TYPE appointment_status_enum ADD VALUE IF NOT EXISTS 'arrived' "
        "AFTER 'confirmed'"
    )
    op.add_column(
        "appointments",
        sa.Column(
            "arrived_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Set when status transitions to ARRIVED.",
        ),
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    # Only drop the column; the enum value stays harmlessly.
    op.drop_column("appointments", "arrived_at")
