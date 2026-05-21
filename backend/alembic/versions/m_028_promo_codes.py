"""m_028 promo_codes + applied_promo_codes

Plan 24 §3 C-2 (Wave 4). Backs the NEW10 welcome credit and any future
promotional codes. Two tables:

  - `promo_codes`        — global catalogue of redeemable codes.
  - `applied_promo_codes` — per-user / per-appointment redemption ledger.

Discount types:
  - "fixed_cents" → discount_amount is the cents to deduct.
  - "percent"     → discount_amount is 1..100 (% off subtotal).

NEW10 is seeded as a fixed_cents code worth 1000¢ ($10) with
`max_redemptions_per_user=1`. Created via app/db/seed_promos.py on
startup; the migration only creates the tables.

Revision ID: m_028
Revises: m_027
Create Date: 2026-05-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_028"
down_revision = "m_027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── promo_codes ──────────────────────────────────────────────────
    op.create_table(
        "promo_codes",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_type", sa.String(16), nullable=False),
        sa.Column("discount_amount", sa.Integer(), nullable=False),
        sa.Column("min_order_cents", sa.Integer(), nullable=True),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
        sa.Column(
            "max_redemptions_per_user", sa.Integer(),
            nullable=False, server_default=sa.text("1"),
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(),
            nullable=False, server_default=sa.text("true"),
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
        sa.UniqueConstraint("code", name="uq_promo_codes_code"),
        sa.CheckConstraint(
            "discount_type IN ('fixed_cents', 'percent')",
            name="ck_promo_codes_discount_type",
        ),
        sa.CheckConstraint(
            "discount_amount > 0",
            name="ck_promo_codes_discount_positive",
        ),
        sa.CheckConstraint(
            "discount_type != 'percent' OR discount_amount <= 100",
            name="ck_promo_codes_percent_max",
        ),
        sa.CheckConstraint(
            "max_redemptions_per_user >= 1",
            name="ck_promo_codes_per_user_min",
        ),
    )
    op.create_index(
        "ix_promo_codes_active_lookup",
        "promo_codes",
        ["code"],
        postgresql_where=sa.text("is_active = true AND is_deleted = false"),
    )

    # ── applied_promo_codes ──────────────────────────────────────────
    op.create_table(
        "applied_promo_codes",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "promo_code_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("promo_codes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="SET NULL"),
            nullable=True,
            comment="NULL = reserved at signup but not yet redeemed against a booking.",
        ),
        sa.Column("amount_discounted_cents", sa.Integer(), nullable=False),
        sa.Column(
            "applied_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "amount_discounted_cents >= 0",
            name="ck_applied_promo_amount_nonnegative",
        ),
    )
    op.create_index(
        "ix_applied_promo_user",
        "applied_promo_codes",
        ["user_id", "promo_code_id"],
    )
    # One redemption per code per appointment (when an appointment is set).
    op.create_index(
        "uq_applied_promo_appointment",
        "applied_promo_codes",
        ["promo_code_id", "appointment_id"],
        unique=True,
        postgresql_where=sa.text("appointment_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_applied_promo_appointment", table_name="applied_promo_codes")
    op.drop_index("ix_applied_promo_user", table_name="applied_promo_codes")
    op.drop_table("applied_promo_codes")
    op.drop_index("ix_promo_codes_active_lookup", table_name="promo_codes")
    op.drop_table("promo_codes")
