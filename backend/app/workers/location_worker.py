from __future__ import annotations

import asyncio
import json
import logging
import math
from datetime import datetime, timezone

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.h3_service import update_h3_index

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  Geometry helpers                                                    #
# ------------------------------------------------------------------ #

def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin((phi2 - phi1) / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def _heading_delta(h1: float, h2: float) -> float:
    d = abs(h1 - h2) % 360
    return d if d <= 180 else 360 - d


# ------------------------------------------------------------------ #
#  Entry processor                                                     #
# ------------------------------------------------------------------ #

async def _process(data: dict, redis, settings) -> None:
    detailer_id: str = data.get("detailer_id", "")
    new_lat = float(data["lat"])
    new_lng = float(data["lng"])
    appointment_id: str | None = data.get("appointment_id") or None
    new_heading = float(data["heading"]) if data.get("heading") else None
    ts = data.get("ts") or datetime.now(timezone.utc).isoformat()

    last_key = f"last_push:{detailer_id}"
    raw_last = await redis.get(last_key)

    old_lat: float | None = None
    old_lng: float | None = None

    if raw_last:
        last = json.loads(raw_last)
        old_lat, old_lng = float(last["lat"]), float(last["lng"])
        dist = _haversine_meters(old_lat, old_lng, new_lat, new_lng)

        old_heading = last.get("heading")
        if old_heading is not None and new_heading is not None:
            hdelta = _heading_delta(float(old_heading), new_heading)
        else:
            hdelta = 0.0

        if (
            dist < settings.FIREBALL_DISTANCE_METERS
            and hdelta < settings.FIREBALL_HEADING_DEGREES
        ):
            # Still refresh active TTL so detailer stays discoverable
            await redis.setex(
                f"active:{detailer_id}", settings.DETAILER_ACTIVE_TTL_SECONDS, "1"
            )
            return  # Fireball: discard duplicate

    # Update last known position
    last_payload: dict = {"lat": new_lat, "lng": new_lng, "ts": ts}
    if new_heading is not None:
        last_payload["heading"] = new_heading
    await redis.set(last_key, json.dumps(last_payload))

    # Persist location + H3 index to PostgreSQL
    try:
        async with AsyncSessionLocal() as db:
            await update_h3_index(
                detailer_id=detailer_id,
                new_lat=new_lat,
                new_lng=new_lng,
                old_lat=old_lat,
                old_lng=old_lng,
                redis=redis,
                db=db,
            )
    except Exception as exc:
        logger.warning("location_worker DB error | detailer=%s err=%s", detailer_id, exc)

    # Broadcast to appointment WS room via Pub/Sub
    if appointment_id:
        try:
            await redis.publish(
                f"ws:room:{appointment_id}",
                json.dumps({"type": "location_update", "lat": new_lat, "lng": new_lng, "ts": ts}),
            )
        except Exception as exc:
            logger.warning("location_worker publish error: %s", exc)


# ------------------------------------------------------------------ #
#  Worker loop                                                         #
# ------------------------------------------------------------------ #

async def location_worker(app_state) -> None:
    redis = app_state.redis
    settings = get_settings()
    last_id = "$"  # Only consume messages arriving after startup

    logger.info("Location worker started")
    while True:
        try:
            messages = await redis.xread({"location_updates": last_id}, block=1000, count=10)
        except asyncio.CancelledError:
            logger.info("Location worker stopped")
            return
        except Exception as exc:
            logger.error("location_worker XREAD error: %s", exc)
            await asyncio.sleep(1)
            continue

        if not messages:
            continue

        for _stream, entries in messages:
            for msg_id, data in entries:
                last_id = msg_id
                try:
                    await _process(data, redis, settings)
                except Exception as exc:
                    logger.error("location_worker _process error | id=%s err=%s", msg_id, exc)
