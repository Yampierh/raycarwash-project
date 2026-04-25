from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.h3.client import find_nearby_detailers

logger = logging.getLogger(__name__)

OFFER_TIMEOUT_SECONDS = 15
MAX_CANDIDATES = 3


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((phi2 - phi1) / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def score(profile, client_lat: float, client_lng: float) -> float:
    """0.4*(1/distance) + 0.4*rating + 0.2*response_rate. Returns 0 if no location."""
    if profile.current_lat is None or profile.current_lng is None:
        return 0.0
    dist = max(
        _haversine_miles(
            float(profile.current_lat), float(profile.current_lng),
            client_lat, client_lng,
        ),
        0.01,
    )
    rating        = float(profile.average_rating or 3.0)
    response_rate = float(profile.response_rate or 0.5)
    return 0.4 * (1.0 / dist) + 0.4 * rating + 0.2 * response_rate


async def assign(
    appointment_id: str,
    client_lat: float,
    client_lng: float,
    redis,
    db: AsyncSession,
    app_state,
) -> None:
    from app.models.models import (
        Appointment,
        AppointmentAssignment,
        AppointmentStatus,
        AssignmentStatus,
        ProviderProfile,
    )

    appt_uuid = uuid.UUID(appointment_id)

    detailer_ids = await find_nearby_detailers(client_lat, client_lng, 25.0, redis)
    if not detailer_ids:
        await _mark_no_detailer(appt_uuid, db)
        return

    result = await db.execute(
        select(ProviderProfile).where(
            ProviderProfile.user_id.in_([uuid.UUID(d) for d in detailer_ids]),
            ProviderProfile.is_accepting_bookings.is_(True),
            ProviderProfile.is_deleted.is_(False),
        )
    )
    profiles = result.scalars().all()

    if not profiles:
        await _mark_no_detailer(appt_uuid, db)
        return

    ranked = sorted(profiles, key=lambda p: score(p, client_lat, client_lng), reverse=True)

    for profile in ranked[:MAX_CANDIDATES]:
        detailer_id_str = str(profile.user_id)
        lock_key = f"assignment:{appointment_id}"

        acquired = await redis.set(lock_key, detailer_id_str, ex=OFFER_TIMEOUT_SECONDS, nx=True)
        if not acquired:
            continue

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=OFFER_TIMEOUT_SECONDS)
        assignment = AppointmentAssignment(
            appointment_id=appt_uuid,
            detailer_id=profile.user_id,
            status=AssignmentStatus.OFFERED.value,
            offered_at=datetime.now(timezone.utc),
            offer_expires_at=expires_at,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

        await redis.publish(
            f"ws:room:user:{detailer_id_str}",
            json.dumps({
                "type": "offer",
                "appointment_id": appointment_id,
                "assignment_id": str(assignment.id),
                "offer_expires_at": expires_at.isoformat(),
            }),
        )

        event_key = f"{appointment_id}:{detailer_id_str}"
        event = asyncio.Event()
        app_state.assignment_events[event_key] = event

        try:
            await asyncio.wait_for(event.wait(), timeout=float(OFFER_TIMEOUT_SECONDS))
            response = app_state.assignment_responses.pop(event_key, None)
            if response == "accepted":
                logger.info("Assignment accepted | appt=%s detailer=%s", appointment_id, detailer_id_str)
                return
            await db.execute(
                update(AppointmentAssignment)
                .where(AppointmentAssignment.id == assignment.id)
                .values(status=AssignmentStatus.DECLINED.value, responded_at=datetime.now(timezone.utc))
            )
            await db.commit()

        except asyncio.TimeoutError:
            logger.info("Offer timed out | appt=%s detailer=%s", appointment_id, detailer_id_str)
            await db.execute(
                update(AppointmentAssignment)
                .where(AppointmentAssignment.id == assignment.id)
                .values(status=AssignmentStatus.TIMEOUT.value, responded_at=datetime.now(timezone.utc))
            )
            await db.commit()

        finally:
            app_state.assignment_events.pop(event_key, None)
            await redis.delete(lock_key)

    await _mark_no_detailer(appt_uuid, db)


async def _mark_no_detailer(appointment_id: uuid.UUID, db: AsyncSession) -> None:
    from app.models.models import Appointment, AppointmentStatus
    await db.execute(
        update(Appointment)
        .where(Appointment.id == appointment_id)
        .values(status=AppointmentStatus.NO_DETAILER_FOUND)
    )
    await db.commit()
    logger.info("No detailer found | appt=%s", appointment_id)
