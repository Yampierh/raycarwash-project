"""drop client_profiles.payment_methods JSONB column

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-25

Removes client_profiles.payment_methods (JSONB).

Reason: local storage of Stripe payment method data creates a silent stale-data
problem. Cards expire, are updated, or are removed in Stripe without the DB
knowing, causing the local copy to drift from reality.

Replacement: query live from Stripe at the point of use:
  stripe.PaymentMethod.list(customer=user.stripe_customer_id, type="card")

The column was nullable with no application code reading from it (confirmed by
grep — no router, schema, or service referenced it). The drop is safe and
non-destructive for existing data.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("client_profiles", "payment_methods")


def downgrade() -> None:
    op.add_column(
        "client_profiles",
        sa.Column(
            "payment_methods",
            JSONB,
            nullable=True,
            comment=(
                "Stored payment preferences — DEPRECATED. "
                "Query from Stripe directly instead."
            ),
        ),
    )
