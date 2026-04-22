from __future__ import annotations

import asyncio
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.h3_service import update_h3_index
from app.ws.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)
settings = get_settings()

STREAM_NAME     = "location_updates"
CONSUMER_GROUP  = "location_worker_group"
CONSUMER_NAME   = "worker-1"


# ------------------------------------------------------------------ #
#  Fireball filter                                                    #
# ------------------------------------------------------------------ #

def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def _should_push(
    redis_client: aioredis.Redis,
    detailer_id: str,
    new_lat: float,
    new_lng: float,
) -> bool:
    """
    Fireball filter: return True only if the position or heading changed
    beyond the configured thresholds.

    This prevents broadcasting every single GPS tick when the detailer
    is stationary — eliminates the polling anti-pattern at the push layer.
    """
    last = await redis_client.hgetall(f"last_push:{detailer_id}")
    if not last:
        return True

    distance = _haversine_meters(
        float(last["lat"]), float(last["lng"]),
        new_lat, new_lng,
    )
    return distance >= settings.FIREBALL_DISTANCE_THRESHOLD_METERS


async def _update_last_push(
    redis_client: aioredis.Redis,
    detailer_id: str,
    lat: float,
    lng: float,
) -> None:
    await redis_client.hset(
        f"last_push:{detailer_id}",
        mapping={"lat": str(lat), "lng": str(lng)},
    )
    await redis_client.expire(f"last_push:{detailer_id}", settings.DETAILER_ACTIVE_TTL_SECONDS)


# ------------------------------------------------------------------ #
#  Main processing loop                                              #
# ------------------------------------------------------------------ #

async def _process_message(
    redis_client: aioredis.Redis,
    ws_manager: ConnectionManager,
    message_id: str,
    fields: dict[str, str],
) -> None:
    detailer_id    = fields["detailer_id"]
    appointment_id = fields["appointment_id"]
    new_lat        = float(fields["lat"])
    new_lng        = float(fields["lng"])

    # Always persist to PostgreSQL (source of truth) and refresh H3/active TTL
    old_lat: float | None = None
    old_lng: float | None = None

    async with AsyncSessionLocal() as db:
        from app.repositories.detailer_repository import DetailerRepository
        repo = DetailerRepository(db)
        profile = await repo.get_profile(uuid.UUID(detailer_id))

        if profile:
            old_lat = float(profile.current_lat) if profile.current_lat else None
            old_lng = float(profile.current_lng) if profile.current_lng else None

        new_cell_r7, new_cell_r9 = await update_h3_index(
            redis_client,
            detailer_id,
            new_lat,
            new_lng,
            old_lat,
            old_lng,
        )

        await repo.update_location(
            uuid.UUID(detailer_id),
            new_lat,
            new_lng,
            h3_index_r7=new_cell_r7,
            h3_index_r9=new_cell_r9,
        )
        await db.commit()

    # Fireball: only broadcast if position changed significantly
    if await _should_push(redis_client, detailer_id, new_lat, new_lng):
        await ws_manager.broadcast(
            appointment_id,
            {
                "type":       "location_update",
                "lat":        new_lat,
                "lng":        new_lng,
                "detailer_id": detailer_id,
                "ts":         datetime.now(timezone.utc).isoformat(),
            },
        )
        await _update_last_push(redis_client, detailer_id, new_lat, new_lng)


async def run(redis_client: aioredis.Redis, ws_manager: ConnectionManager) -> None:
    """
    Redis Streams consumer loop.

    Creates the consumer group on first run (idempotent), then processes
    messages in a tight loop. On error, waits 1 second before retrying
    to avoid hammering Redis during transient failures.
    """
    try:
        await redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info("Location Worker consumer group created.")
    except Exception:
        pass  # Group already exists — expected on restart

    logger.info("Location Worker started — consuming stream '%s'", STREAM_NAME)

    while True:
        try:
            results = await redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_NAME: ">"},
                count=10,
                block=1000,
            )

            if not results:
                continue

            for _stream, messages in results:
                for message_id, fields in messages:
                    try:
                        await _process_message(redis_client, ws_manager, message_id, fields)
                        await redis_client.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
                    except Exception as exc:
                        logger.error(
                            "Location Worker message error | id=%s err=%s",
                            message_id, exc,
                        )

        except asyncio.CancelledError:
            logger.info("Location Worker shutting down.")
            break
        except Exception as exc:
            logger.error("Location Worker loop error: %s", exc)
            await asyncio.sleep(1)
