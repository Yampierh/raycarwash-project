"""
workers/login_history_purger.py — Enforces the UserLoginHistory retention
policy defined in ADR-005 + plan §9.

Retention:
  - was_successful=True  → 12 months
  - was_successful=False →  3 months (90 days)

Runs monthly via rq-scheduler. The job is idempotent — re-runs on the same
day are a no-op once the window has caught up.

Cleanup is bulk DELETE (no audit log entry — these rows ARE the audit log
for logins, and bulk-purging them is the whole point of the retention
policy). The action `USER_LOGIN_HISTORY_PURGED` is recorded ONCE per run
in the regular audit_log so admins can trace when the worker ran.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from domains.auth.models import UserLoginHistory
from infrastructure.db.session import AsyncSessionLocal

logger = logging.getLogger("raycarwash.workers.login_history_purger")

_SUCCESSFUL_RETENTION = timedelta(days=365)
_FAILED_RETENTION = timedelta(days=90)


async def _purge_with_session(session) -> dict:
    """Inner helper — accepts a caller-owned session so tests can drive it
    without re-opening `AsyncSessionLocal` (the engine is tied to the
    enclosing event loop)."""
    now = datetime.now(timezone.utc)
    cutoff_success = now - _SUCCESSFUL_RETENTION
    cutoff_failure = now - _FAILED_RETENTION

    success_count = await session.scalar(
        select(func.count())
        .select_from(UserLoginHistory)
        .where(
            UserLoginHistory.was_successful.is_(True),
            UserLoginHistory.login_at < cutoff_success,
        )
    ) or 0
    failure_count = await session.scalar(
        select(func.count())
        .select_from(UserLoginHistory)
        .where(
            UserLoginHistory.was_successful.is_(False),
            UserLoginHistory.login_at < cutoff_failure,
        )
    ) or 0

    if success_count:
        await session.execute(
            delete(UserLoginHistory).where(
                UserLoginHistory.was_successful.is_(True),
                UserLoginHistory.login_at < cutoff_success,
            )
        )
    if failure_count:
        await session.execute(
            delete(UserLoginHistory).where(
                UserLoginHistory.was_successful.is_(False),
                UserLoginHistory.login_at < cutoff_failure,
            )
        )

    stats = {"successful_purged": int(success_count), "failed_purged": int(failure_count)}
    if stats["successful_purged"] or stats["failed_purged"]:
        logger.info("login_history_purger: %s", stats)
    return stats


async def _run_once() -> dict:
    """Production entry point — opens a fresh session via AsyncSessionLocal."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            return await _purge_with_session(session)


def run() -> dict:
    return asyncio.run(_run_once())
