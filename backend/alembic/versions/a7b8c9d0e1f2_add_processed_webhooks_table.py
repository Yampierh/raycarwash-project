"""add processed_webhooks table for Stripe idempotency

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-25

Stripe guarantees at-least-once delivery. The same webhook event can arrive
multiple times (network retries, Stripe retries on non-2xx). Without tracking,
critical handlers like payment_intent.succeeded could be processed twice,
causing double-fulfillment or double-credit.

Pattern used in the webhook router:
  INSERT INTO processed_webhooks (stripe_event_id, event_type)
  VALUES (:id, :type)
  ON CONFLICT (stripe_event_id) DO NOTHING
  → if rowcount == 0: already processed, return 200 immediately
  → if rowcount == 1: new event, proceed with handler

The primary key on stripe_event_id is the uniqueness guarantee.
No foreign keys — event IDs are Stripe-owned identifiers (evt_xxxxxxxx).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_webhooks",
        sa.Column(
            "stripe_event_id",
            sa.String(64),
            primary_key=True,
            comment="Stripe event ID (evt_xxxxxxxx). PK enforces uniqueness.",
        ),
        sa.Column(
            "event_type",
            sa.String(80),
            nullable=False,
            comment="Stripe event type, e.g. 'payment_intent.succeeded'.",
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Index on processed_at for periodic cleanup of old records
    op.create_index(
        "ix_processed_webhooks_processed_at",
        "processed_webhooks",
        ["processed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_processed_webhooks_processed_at", table_name="processed_webhooks")
    op.drop_table("processed_webhooks")
