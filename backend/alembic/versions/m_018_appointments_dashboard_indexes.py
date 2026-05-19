"""m_018 add appointments dashboard indexes

Plan 20 §17.5 (M01) + Plan 21 §7.5 — compound indexes that turn the
provider and customer dashboard aggregates from sequential scans into
index scans as the appointments table grows.

Per Plan 22 §6.1 corrections (D1, D2, D3, D7) the SQL uses the real
column names: `detailer_id`, `client_id`, `estimated_price`,
lowercase enum value `'completed'`.

Indexes created:

  1. ix_appointments_detailer_status_time
     ON (detailer_id, status, scheduled_time DESC) WHERE NOT is_deleted
     → Backs GET /api/v1/detailers/me/jobs?status=... and the dashboard
       upcoming-jobs section. DESC ordering on scheduled_time matches
       the "most recent first" query pattern.

  2. ix_appointments_detailer_completed
     ON (detailer_id, completed_at) INCLUDE (estimated_price)
     WHERE status = 'completed' AND NOT is_deleted
     → Backs GET /api/v1/detailers/me/earnings/{summary,ledger}.
       Covering index — enables index-only scan for the SUM aggregate.
       `status` is dropped from the key column list (redundant with
       the WHERE clause filtering to a single value).

  3. ix_appointments_detailer_client
     ON (detailer_id, client_id, status) WHERE NOT is_deleted
     → Backs GET /api/v1/detailers/me/customers (per-client visits).

  4. ix_appointments_client_status_time
     ON (client_id, status, scheduled_time) WHERE NOT is_deleted
     → Backs GET /api/v1/customers/me/dashboard upcoming-appointment.

Indexes NOT created here (deliberate omissions):

  - "today's route" partial index (Plan 20 M01 #4) — the contract
    specified `WHERE scheduled_time::date = CURRENT_DATE` but
    PostgreSQL requires partial-index predicates to be IMMUTABLE
    (CURRENT_DATE is STABLE). Index #1 above already serves this
    query with a runtime WHERE on the same columns.

  - ix_rewards_user_id (Plan 21 §7.5) — the `rewards` table does not
    exist yet. Will be added alongside the rewards table migration.

  - mv_provider_earnings_daily (Plan 20 §17.5 M02) — deferred to a
    later migration after the earnings endpoint lands, so it can be
    validated against real data.

Revision ID: m_018
Revises: m_017
Create Date: 2026-05-19
"""
from __future__ import annotations

from alembic import op

revision = "m_018"
down_revision = "m_017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Dashboard upcoming jobs, jobs list with status filter.
    # Raw SQL because alembic's `op.create_index` doesn't expose
    # per-column ASC/DESC ordering with string columns.
    op.execute(
        "CREATE INDEX ix_appointments_detailer_status_time "
        "ON appointments (detailer_id, status, scheduled_time DESC) "
        "WHERE NOT is_deleted"
    )

    # 2. Earnings aggregation — covering index for SUM(estimated_price).
    # Raw SQL because alembic's `op.create_index` doesn't support the
    # `INCLUDE` clause uniformly across versions.
    op.execute(
        "CREATE INDEX ix_appointments_detailer_completed "
        "ON appointments (detailer_id, completed_at) "
        "INCLUDE (estimated_price) "
        "WHERE status = 'completed' AND NOT is_deleted"
    )

    # 3. Customer aggregation — visits per (detailer, client).
    op.create_index(
        "ix_appointments_detailer_client",
        "appointments",
        ["detailer_id", "client_id", "status"],
        postgresql_where="NOT is_deleted",
    )

    # 4. Customer dashboard — upcoming appointment lookup.
    op.create_index(
        "ix_appointments_client_status_time",
        "appointments",
        ["client_id", "status", "scheduled_time"],
        postgresql_where="NOT is_deleted",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_appointments_client_status_time", table_name="appointments",
    )
    op.drop_index(
        "ix_appointments_detailer_client", table_name="appointments",
    )
    op.execute("DROP INDEX IF EXISTS ix_appointments_detailer_completed")
    op.execute("DROP INDEX IF EXISTS ix_appointments_detailer_status_time")
