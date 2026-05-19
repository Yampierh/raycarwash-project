"""m_019 add Stripe Connect onboarding columns to provider_profiles

Plan 20 §17.5 (M03) — adds the columns needed to expose Stripe Connect
state on `GET /api/v1/detailers/me/connect-account/status` and to drive
the H10 fix (expire abandoned onboarding URLs after 24h).

Plan 20 §17.5 originally specified two columns
(`stripe_onboarding_status`, `stripe_onboarding_expires_at`). The audit
review (Plan 22 §6.1.2 paragraph "M03 columns") widened the scope to
five — without `stripe_account_id` the profile can't be linked to the
Stripe Connect account, and without the `payouts_enabled` /
`charges_enabled` mirrors every status read would round-trip to Stripe.

Columns added (all on provider_profiles):

  - stripe_account_id            VARCHAR(64), nullable, unique
                                 Stripe `acct_...` identifier. Nullable
                                 because not every provider has started
                                 onboarding.

  - stripe_onboarding_status     VARCHAR(20), NOT NULL, default 'not_started'
                                 Local FSM:
                                   not_started → pending → completed
                                                       ╲→ expired
                                                       ╲→ rejected

  - stripe_onboarding_expires_at TIMESTAMPTZ, nullable
                                 Set to NOW() + 24h when a Stripe
                                 onboarding URL is generated. The
                                 hourly worker flips `pending` rows
                                 past this timestamp to `expired`.

  - stripe_payouts_enabled       BOOLEAN, NOT NULL, default false
                                 Mirror of Stripe's payouts_enabled,
                                 updated by the account.updated webhook.

  - stripe_charges_enabled       BOOLEAN, NOT NULL, default false
                                 Mirror of Stripe's charges_enabled.

Revision ID: m_019
Revises: m_018
Create Date: 2026-05-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m_019"
down_revision = "m_018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "provider_profiles",
        sa.Column("stripe_account_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "stripe_onboarding_status",
            sa.String(20),
            nullable=False,
            server_default="not_started",
        ),
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "stripe_onboarding_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "stripe_payouts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "stripe_charges_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Unique index — Stripe account IDs are globally unique. Postgres
    # treats NULL values as distinct, so multiple profiles without an
    # account_id can coexist (the common case before onboarding).
    op.create_index(
        "ix_provider_profiles_stripe_account_id",
        "provider_profiles",
        ["stripe_account_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_profiles_stripe_account_id",
        table_name="provider_profiles",
    )
    op.drop_column("provider_profiles", "stripe_charges_enabled")
    op.drop_column("provider_profiles", "stripe_payouts_enabled")
    op.drop_column("provider_profiles", "stripe_onboarding_expires_at")
    op.drop_column("provider_profiles", "stripe_onboarding_status")
    op.drop_column("provider_profiles", "stripe_account_id")
