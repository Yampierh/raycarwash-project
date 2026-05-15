"""
workers/pending_contact_cleanup.py — Drops expired pending_contact_changes.

Runs hourly via rq-scheduler. Removes:
  - rows whose `expires_at < now()` AND `consumed_at IS NULL` (never used,
    no longer valid).

Successfully consumed rows are kept indefinitely — they form part of the
audit trail and the row size is tiny (one encrypted blob + a hash).

Per plan §14.4 — the worker runs in the `low` priority queue. The RQ
job is enqueued by `workers/schedule.py`.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete

from domains.users.pending_contact_change import PendingContactChange
from infrastructure.db.session import AsyncSessionLocal

logger = logging.getLogger("raycarwash.workers.pending_contact_cleanup")


async def _cleanup_with_session(session) -> int:
    """Inner helper — caller owns the session/transaction. Used by tests
    so they can re-use their fixture session without spinning up a fresh
    AsyncSessionLocal tied to a different event loop."""
    now = datetime.now(timezone.utc)
    stmt = (
        delete(PendingContactChange)
        .where(
            PendingContactChange.expires_at < now,
            PendingContactChange.consumed_at.is_(None),
        )
        .returning(PendingContactChange.id)
    )
    result = await session.execute(stmt)
    removed = list(result.scalars().all())
    if removed:
        logger.info("pending_contact_cleanup removed %d expired rows", len(removed))
    return len(removed)


async def _run_once() -> int:
    """Production entry point — opens a fresh session via AsyncSessionLocal."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            return await _cleanup_with_session(session)


def run() -> int:
    """Entry point for `rq enqueue`. Bridges async → sync."""
    return asyncio.run(_run_once())
