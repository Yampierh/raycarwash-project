"""m_007 create payment_methods

Mirrors the Stripe Customer's payment methods locally so the Profile
Hub can show "**** 4242 Visa" without round-tripping to Stripe on every
read. Mutations originate either through `/users/me/payment-methods/
setup-intent` (user-initiated) or through the
`payment_method.{attached,detached,updated}` webhooks (Stripe-initiated,
e.g. card expiration update).

We deliberately store ONLY non-PCI fields. Anything sensitive (full PAN,
CVV, cardholder name when present) stays exclusively in Stripe.

Revision ID: m_007
Revises: m_006
Create Date: 2026-05-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_007"
down_revision = "m_006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Stripe is the source of truth — pm_xxx ID is the join key.
        sa.Column("stripe_payment_method_id", sa.String(64), nullable=False, unique=True),
        # "card" | "us_bank_account" | "apple_pay" | "google_pay". String for
        # forward-compat with future Stripe types.
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("brand", sa.String(20), nullable=True),     # "visa", "mastercard", ...
        sa.Column("last4", sa.String(4), nullable=True),
        sa.Column("exp_month", sa.Integer, nullable=True),
        sa.Column("exp_year", sa.Integer, nullable=True),
        sa.Column("billing_zip", sa.String(20), nullable=True),
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

    # Per-user listing.
    op.create_index(
        "idx_payment_methods_user_active",
        "payment_methods",
        ["user_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # One default payment method per user.
    op.create_index(
        "idx_payment_methods_default_unique",
        "payment_methods",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true AND is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("idx_payment_methods_default_unique", table_name="payment_methods")
    op.drop_index("idx_payment_methods_user_active", table_name="payment_methods")
    op.drop_table("payment_methods")
