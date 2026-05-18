"""m_017 drop provider_profiles.is_accepting_bookings

Integration plan E1.E (01-profiles.md §7, step 7). The canonical flag
that gates whether a provider shows up to clients is now `is_active`
(added in m_015 + dual-written across E1.B/D). This migration finishes
the rename by dropping the legacy column.

`ProviderProfile.is_accepting_bookings` survives as a Python
`@property` on the model that forwards to `is_active` so legacy
callers (Phase 5 service, Pydantic schemas, etc.) continue to work
without a wire change. The mobile/web/marketing JSON contract
(`is_accepting_bookings: bool`) stays — the field is just read from
the @property now.

Revision ID: m_017
Revises: m_016
Create Date: 2026-05-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m_017"
down_revision = "m_016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("provider_profiles", "is_accepting_bookings")


def downgrade() -> None:
    op.add_column(
        "provider_profiles",
        sa.Column(
            "is_accepting_bookings",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    # Backfill from is_active so a re-upgrade after downgrade preserves
    # the gating state.
    op.execute(
        "UPDATE provider_profiles SET is_accepting_bookings = is_active"
    )
