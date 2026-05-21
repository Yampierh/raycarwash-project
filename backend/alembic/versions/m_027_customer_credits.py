"""m_027 customer_credits ledger table

Plan 24 W2-E. New table to back the comp-credit endpoint
`POST /api/v1/admin/customers/{id}/credits` and the customers-segment
view's `credit_balance_cents` aggregate.

Each row is a balance-affecting event (positive issue, negative consume/
revoke). Wallet balance = SUM(amount_cents) WHERE status='active'.

Revision ID: m_027
Revises: m_026
Create Date: 2026-05-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_027"
down_revision = "m_026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_credits",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column(
            "currency", sa.String(3),
            nullable=False, server_default="USD",
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "source", sa.String(16),
            nullable=False, server_default="admin_comp",
        ),
        sa.Column(
            "status", sa.String(16),
            nullable=False, server_default="active",
        ),
        sa.Column(
            "issued_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "related_appointment_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True,
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
        sa.CheckConstraint(
            "amount_cents != 0",
            name="ck_customer_credits_amount_nonzero",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'consumed', 'expired', 'revoked')",
            name="ck_customer_credits_status",
        ),
        sa.CheckConstraint(
            "source IN ('admin_comp', 'promo', 'referral', 'refund', 'adjustment')",
            name="ck_customer_credits_source",
        ),
    )
    op.create_index(
        "ix_customer_credits_user_id", "customer_credits", ["user_id"],
    )
    op.create_index(
        "ix_customer_credits_user_active",
        "customer_credits",
        ["user_id"],
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_customer_credits_user_active", table_name="customer_credits")
    op.drop_index("ix_customer_credits_user_id", table_name="customer_credits")
    op.drop_table("customer_credits")
