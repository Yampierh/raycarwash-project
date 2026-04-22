from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.services.h3_service import find_nearby_detailers

logger = logging.getLogger(__name__)
settings = get_settings()

_LOCK_KEY          = "assignment:{appointment_id}"
_RESPONSE_KEY      = "assignment_response:{appointment_id}"
_ASSIGNMENT_STREAM = "assignment_queue"


# ------------------------------------------------------------------ #
#  Candidate scoring                                                  #
# ------------------------------------------------------------------ #

@dataclass
class DetailerCandidate:
    detailer_id: str
    distance_miles: float
    rating: float
    response_rate: float


def score(candidate: DetailerCandidate) -> float:
    """
    Composite score for detailer assignment priority.

      distance_score  = 1 / max(distance_miles, 0.1)   (closer is better)
      rating_score    = rating / 5.0                    (normalized 0–1)
      response_score  = response_rate                   (already 0–1)

    Weights are configurable via settings.
    """
    distance_score = 1.0 / max(candidate.distance_miles, 0.1)
    rating_score   = candidate.rating / 5.0
    response_score = candidate.response_rate

    return (
        settings.ASSIGNMENT_SCORE_DISTANCE_WEIGHT  * distance_score
        + settings.ASSIGNMENT_SCORE_RATING_WEIGHT  * rating_score
        + settings.ASSIGNMENT_SCORE_RESPONSE_WEIGHT * response_score
    )


# ------------------------------------------------------------------ #
#  Lock management                                                    #
# ------------------------------------------------------------------ #

async def acquire_assignment_lock(
    redis_client: aioredis.Redis,
    appointment_id: str,
    detailer_id: str,
) -> bool:
    """
    Atomic SET NX EX: acquire the lock only if no other worker holds it.
    TTL = ASSIGNMENT_OFFER_TTL_SECONDS so lock auto-expires if detailer never responds.
    """
    key = _LOCK_KEY.format(appointment_id=appointment_id)
    result = await redis_client.set(
        key, detailer_id,
        ex=settings.ASSIGNMENT_OFFER_TTL_SECONDS,
        nx=True,
    )
    return result is not None


async def release_assignment_lock(
    redis_client: aioredis.Redis,
    appointment_id: str,
) -> None:
    await redis_client.delete(_LOCK_KEY.format(appointment_id=appointment_id))


# ------------------------------------------------------------------ #
#  Offer / response signaling                                         #
# ------------------------------------------------------------------ #

async def signal_response(
    redis_client: aioredis.Redis,
    appointment_id: str,
    accepted: bool,
) -> None:
    """
    Called by the rides router when a detailer accepts or declines.
    Publishes the response so wait_for_response() can unblock.
    """
    key = _RESPONSE_KEY.format(appointment_id=appointment_id)
    await redis_client.set(key, "accepted" if accepted else "declined", ex=60)


async def wait_for_response(
    redis_client: aioredis.Redis,
    appointment_id: str,
    timeout: int,
) -> bool:
    """
    Poll the response key with 0.5s interval until timeout.
    Returns True if accepted, False if declined or timed out.
    """
    key = _RESPONSE_KEY.format(appointment_id=appointment_id)
    elapsed = 0.0
    while elapsed < timeout:
        value = await redis_client.get(key)
        if value == "accepted":
            await redis_client.delete(key)
            return True
        if value == "declined":
            await redis_client.delete(key)
            return False
        await asyncio.sleep(0.5)
        elapsed += 0.5
    return False


# ------------------------------------------------------------------ #
#  Core assignment logic                                              #
# ------------------------------------------------------------------ #

async def assign_appointment(
    redis_client: aioredis.Redis,
    appointment_id: str,
    client_lat: float,
    client_lng: float,
    service_id: str,
) -> bool:
    """
    Main assignment algorithm:
      1. Find active detailers via H3 k-ring
      2. Enrich with profile data (distance, rating, response_rate)
      3. Score and sort candidates
      4. For each top candidate (up to ASSIGNMENT_MAX_CANDIDATES):
           a. Acquire Redis lock (15s TTL)
           b. Push offer notification
           c. Wait for accept/decline response (15s)
           d. On accept: confirm and return True
           e. On decline/timeout: record and try next

    Returns True if successfully assigned, False if all candidates exhausted.
    """
    from app.db.session import AsyncSessionLocal
    from app.repositories.detailer_repository import DetailerRepository
    import math

    nearby_ids = await find_nearby_detailers(redis_client, client_lat, client_lng)
    if not nearby_ids:
        logger.warning("No active detailers found for appointment=%s", appointment_id)
        return False

    # Enrich candidates with DB profile data
    candidates: list[DetailerCandidate] = []
    async with AsyncSessionLocal() as db:
        repo = DetailerRepository(db)
        for did in nearby_ids:
            profile = await repo.get_profile(uuid.UUID(did))
            if profile is None or not profile.is_accepting_bookings:
                continue
            if profile.current_lat is None or profile.current_lng is None:
                continue

            # Haversine distance in miles
            lat1, lng1 = float(profile.current_lat), float(profile.current_lng)
            R = 3958.8
            phi1, phi2 = math.radians(lat1), math.radians(client_lat)
            a = (
                math.sin(math.radians(client_lat - lat1) / 2) ** 2
                + math.cos(phi1) * math.cos(phi2)
                * math.sin(math.radians(client_lng - lng1) / 2) ** 2
            )
            dist = 2 * R * math.asin(math.sqrt(a))

            # Check service radius
            if dist > profile.service_radius_miles:
                continue

            candidates.append(DetailerCandidate(
                detailer_id=did,
                distance_miles=dist,
                rating=float(profile.average_rating or 0.0),
                response_rate=float(profile.response_rate or 0.5),
            ))

    if not candidates:
        logger.warning("No eligible candidates for appointment=%s", appointment_id)
        return False

    sorted_candidates = sorted(candidates, key=score, reverse=True)
    max_attempts = min(len(sorted_candidates), settings.ASSIGNMENT_MAX_CANDIDATES)

    for candidate in sorted_candidates[:max_attempts]:
        locked = await acquire_assignment_lock(redis_client, appointment_id, candidate.detailer_id)
        if not locked:
            continue  # Another worker already claimed this appointment

        logger.info(
            "Offering appointment=%s to detailer=%s",
            appointment_id, candidate.detailer_id,
        )
        await _push_offer(redis_client, appointment_id, candidate.detailer_id)

        accepted = await wait_for_response(
            redis_client,
            appointment_id,
            timeout=settings.ASSIGNMENT_OFFER_TTL_SECONDS,
        )

        if accepted:
            await _confirm_assignment(appointment_id, candidate.detailer_id)
            return True

        # Declined or timeout — release lock and try next
        await release_assignment_lock(redis_client, appointment_id)
        await _record_outcome(appointment_id, candidate.detailer_id, "declined")

    return False


async def _push_offer(
    redis_client: aioredis.Redis,
    appointment_id: str,
    detailer_id: str,
) -> None:
    """
    Notify the detailer of a pending offer via WebSocket (Pub/Sub).
    In production this would also trigger a push notification (FCM/APNs).
    """
    await redis_client.publish(
        f"ws:room:detailer:{detailer_id}",
        f'{{"type":"assignment_offer","appointment_id":"{appointment_id}"}}',
    )


async def _confirm_assignment(appointment_id: str, detailer_id: str) -> None:
    from app.db.session import AsyncSessionLocal
    from app.repositories.appointment_repository import AppointmentRepository
    from app.models.models import AppointmentStatus
    import uuid

    async with AsyncSessionLocal() as db:
        repo = AppointmentRepository(db)
        appt = await repo.get_by_id(uuid.UUID(appointment_id))
        if appt:
            appt.detailer_id = uuid.UUID(detailer_id)
            appt.status      = AppointmentStatus.CONFIRMED
            await db.commit()
    logger.info("Assignment confirmed | appointment=%s detailer=%s", appointment_id, detailer_id)


async def _record_outcome(appointment_id: str, detailer_id: str, status: str) -> None:
    from app.db.session import AsyncSessionLocal
    from app.models.ledger import AppointmentAssignment
    from datetime import datetime, timezone
    import uuid

    async with AsyncSessionLocal() as db:
        record = AppointmentAssignment(
            id=uuid.uuid4(),
            appointment_id=uuid.UUID(appointment_id),
            detailer_id=uuid.UUID(detailer_id),
            offered_at=datetime.now(timezone.utc),
            responded_at=datetime.now(timezone.utc),
            status=status,
            offer_expires_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.commit()
