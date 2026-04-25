"""replace onboarding_completed bool with onboarding_status state machine

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-25

Replaces the binary onboarding_completed: bool with a VARCHAR state machine
field that can accommodate future onboarding steps without further migrations.

States:
  pending_profile      — registered, full_name / role not yet set (was FALSE)
  pending_verification — provider submitted docs, awaiting admin approval
  completed            — all steps done; full API access granted (was TRUE)

Stored as VARCHAR(30) — adding new states is a code-only change.

Steps:
  1. Add onboarding_status VARCHAR(30) DEFAULT 'pending_profile'
  2. Backfill: TRUE  → 'completed', FALSE → 'pending_profile'
  3. Add NOT NULL constraint (all rows now have a value)
  4. Drop onboarding_completed column
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None

_TABLE = "users"
_NEW_COL = "onboarding_status"
_OLD_COL = "onboarding_completed"


def upgrade() -> None:
    # Step 1: add nullable first (required for backfill before NOT NULL)
    op.add_column(
        _TABLE,
        sa.Column(_NEW_COL, sa.String(30), nullable=True),
    )

    # Step 2: backfill from the old bool column
    op.execute(f"""
        UPDATE {_TABLE}
        SET {_NEW_COL} = CASE
            WHEN {_OLD_COL} = TRUE  THEN 'completed'
            ELSE                          'pending_profile'
        END
    """)

    # Step 3: tighten to NOT NULL with server default for future inserts
    op.alter_column(
        _TABLE, _NEW_COL,
        nullable=False,
        server_default="pending_profile",
    )

    # Step 4: drop the old column — no longer needed
    op.drop_column(_TABLE, _OLD_COL)


def downgrade() -> None:
    # Restore onboarding_completed bool from onboarding_status
    op.add_column(
        _TABLE,
        sa.Column(_OLD_COL, sa.Boolean(), nullable=True),
    )
    op.execute(f"""
        UPDATE {_TABLE}
        SET {_OLD_COL} = ({_NEW_COL} = 'completed')
    """)
    op.alter_column(_TABLE, _OLD_COL, nullable=False, server_default="false")
    op.drop_column(_TABLE, _NEW_COL)
