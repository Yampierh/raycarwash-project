"""
workers/session_cleanup_worker.py — Plan 23 Fase 8.

Daily worker that keeps the `sessions` table from growing unbounded:

  1. **Auto-revoke** active Session rows whose backing refresh-token
     family has expired beyond a grace period. (A refresh token's TTL
     IS the session's expiration; we shouldn't leave a Session row
     `revoked=False` after the user can no longer rotate.)
  2. **Hard-delete** Session rows that have been revoked for longer
     than `_HARD_DELETE_AFTER_DAYS`. The data is no longer useful for
     UX (the user moved on) and just bloats the table.
  3. **Evict** the Redis cache entry for any session it touched so the
     next request sees the fresh state immediately instead of waiting
     for the 5-minute TTL.

Stats are logged at INFO at the end of every run for observability.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update

from domains.auth.models import RefreshToken, Session
from infrastructure.db.session import AsyncSessionLocal

logger = logging.getLogger("raycarwash.workers.session_cleanup")


_INTERVAL_SECONDS = 24 * 60 * 60  # run once a day
_GRACE_PERIOD_DAYS = 1            # let an expired family linger 1 day so a
                                  # last-minute refresh has a chance to land
_HARD_DELETE_AFTER_DAYS = 90      # purge revoked rows older than 3 months


async def _evict_caches(app_state, session_ids: list) -> int:
    """Best-effort: drop the cached session row + last_seen throttle for
    every session id we just changed. Returns count of evictions
    attempted (not necessarily successful — redis may be down)."""
    redis = getattr(app_state, "redis", None) if app_state else None
    if redis is None or not session_ids:
        return 0
    attempted = 0
    for sid in session_ids:
        try:
            await redis.delete(f"session:{sid}")
            await redis.delete(f"session:last_seen:{sid}")
            attempted += 1
        except Exception as exc:
            logger.warning("session_cleanup cache evict failed for %s (%s)", sid, exc)
    return attempted


async def _run_once(app_state=None) -> dict:
    """Single sweep. Returns stats; callable directly from tests."""
    now = datetime.now(timezone.utc)
    expired_cutoff = now - timedelta(days=_GRACE_PERIOD_DAYS)
    hard_delete_cutoff = now - timedelta(days=_HARD_DELETE_AFTER_DAYS)

    async with AsyncSessionLocal() as db:
        # ── 1) Auto-revoke sessions whose family has expired past grace
        #
        # A session "expires" when every refresh token in its family has
        # expired. Simpler proxy: the MAX(expires_at) of the family.
        # If that's older than `now - grace`, the family is done.
        expired_sessions_stmt = (
            select(Session.id)
            .join(RefreshToken, RefreshToken.family_id == Session.family_id)
            .where(Session.revoked.is_(False))
            .group_by(Session.id)
            # HAVING MAX(refresh.expires_at) < cutoff — express via subquery
        )
        # We don't have aggregate in select_from convenient here; use a
        # straightforward two-step approach.
        from sqlalchemy import func as sa_func
        candidates_q = (
            select(
                Session.id,
                sa_func.max(RefreshToken.expires_at).label("family_expires_at"),
            )
            .join(RefreshToken, RefreshToken.family_id == Session.family_id)
            .where(Session.revoked.is_(False))
            .group_by(Session.id)
        )
        rows = (await db.execute(candidates_q)).all()
        revoke_ids = [
            r.id for r in rows
            if r.family_expires_at and r.family_expires_at < expired_cutoff
        ]

        revoked_count = 0
        if revoke_ids:
            await db.execute(
                update(Session)
                .where(Session.id.in_(revoke_ids))
                .values(revoked=True, revoked_at=now)
            )
            revoked_count = len(revoke_ids)

        # ── 2) Hard-delete rows revoked > 90 days ago
        hard_delete_q = (
            select(Session.id).where(
                Session.revoked.is_(True),
                Session.revoked_at < hard_delete_cutoff,
            )
        )
        delete_ids = [r[0] for r in (await db.execute(hard_delete_q)).all()]
        if delete_ids:
            await db.execute(delete(Session).where(Session.id.in_(delete_ids)))

        await db.commit()

    # ── 3) Cache eviction (post-commit so we don't broadcast a stale
    # state if the commit fails).
    touched = revoke_ids + delete_ids
    evicted = await _evict_caches(app_state, [str(sid) for sid in touched])

    stats = {
        "sessions_revoked": revoked_count,
        "sessions_deleted": len(delete_ids),
        "cache_evicted": evicted,
    }
    if any(v > 0 for v in stats.values()):
        logger.info("session_cleanup: %s", stats)
    return stats


async def session_cleanup_worker(app_state) -> None:
    """Long-running task. Sleeps first so a deploy doesn't immediately
    block startup with a heavy GC pass."""
    logger.info(
        "session_cleanup_worker started — interval=%dh grace=%dd hard_delete_after=%dd",
        _INTERVAL_SECONDS // 3600, _GRACE_PERIOD_DAYS, _HARD_DELETE_AFTER_DAYS,
    )
    while True:
        await asyncio.sleep(_INTERVAL_SECONDS)
        try:
            await _run_once(app_state)
        except asyncio.CancelledError:
            logger.info("session_cleanup_worker shutting down.")
            return
        except Exception:
            logger.exception(
                "session_cleanup_worker error — will retry in %dh",
                _INTERVAL_SECONDS // 3600,
            )
