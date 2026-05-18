"""
workers/achievement_evaluator.py — daily grant of provider badges.

Runs once a day via rq-scheduler. Walks every active detailer and
inserts ProviderAchievement rows for criteria that have just passed.

The (provider_user_id, achievement_type) UNIQUE constraint from m_013
makes the worker idempotent — re-running for a detailer that already
holds a badge is an INSERT … ON CONFLICT DO NOTHING no-op rather than
a 409 storm.

Current catalog (additive — new badge types can land in later phases
without migrations because `achievement_type` is a free-form String):

  - `verified`           verification_status = "approved"
  - `first_job`          total_services_completed >= 1
  - `ten_jobs`           total_services_completed >= 10
  - `hundred_jobs`       total_services_completed >= 100
  - `five_star`          average_rating >= 4.8 AND total_reviews >= 5
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from domains.providers.achievement import ProviderAchievement
from domains.providers.models import ProviderProfile
from infrastructure.db.session import AsyncSessionLocal

logger = logging.getLogger("raycarwash.workers.achievement_evaluator")


def _criteria(profile: ProviderProfile) -> list[tuple[str, dict]]:
    """Return list of (achievement_type, metadata) tuples the profile
    currently satisfies. The worker INSERTs each — ON CONFLICT DO
    NOTHING handles re-runs."""
    earned: list[tuple[str, dict]] = []

    if profile.verification_status == "approved":
        earned.append(("verified", {
            "approved_at": (
                profile.verification_reviewed_at.isoformat()
                if profile.verification_reviewed_at else None
            ),
        }))

    completed = getattr(profile, "total_services_completed", 0) or 0
    if completed >= 1:
        earned.append(("first_job", {"job_count": completed}))
    if completed >= 10:
        earned.append(("ten_jobs", {"job_count": completed}))
    if completed >= 100:
        earned.append(("hundred_jobs", {"job_count": completed}))

    rating = (
        float(profile.average_rating)
        if profile.average_rating is not None else None
    )
    if (
        rating is not None
        and rating >= 4.8
        and profile.total_reviews >= 5
    ):
        earned.append(("five_star", {
            "rating": rating,
            "review_count": profile.total_reviews,
        }))

    return earned


async def _evaluate_with_session(session) -> int:
    """Inner helper — caller owns the transaction. Returns the number
    of newly-granted badges (across all detailers).

    Split out so tests can drive it against the fixture session
    without spinning up AsyncSessionLocal on a different event loop."""
    now = datetime.now(timezone.utc)
    profiles = (await session.scalars(
        select(ProviderProfile)
    )).all()

    granted = 0
    for profile in profiles:
        for achievement_type, metadata in _criteria(profile):
            stmt = (
                pg_insert(ProviderAchievement)
                .values(
                    provider_user_id=profile.user_id,
                    achievement_type=achievement_type,
                    metadata_=metadata,
                    awarded_at=now,
                )
                .on_conflict_do_nothing(
                    index_elements=["provider_user_id", "achievement_type"],
                )
            )
            result = await session.execute(stmt)
            if (result.rowcount or 0) > 0:
                granted += 1
                logger.info(
                    "granted %s to provider=%s metadata=%s",
                    achievement_type, profile.user_id, metadata,
                )

    if granted:
        logger.info("achievement_evaluator granted %d new badges", granted)
    return granted


async def _run_once() -> int:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            return await _evaluate_with_session(session)


def run() -> int:
    """RQ entry point — bridges async → sync."""
    return asyncio.run(_run_once())
