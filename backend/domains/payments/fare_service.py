from __future__ import annotations

import hashlib
import hmac
import math
from datetime import datetime, timezone

import h3

from app.core.config import get_settings


async def calculate_surge(lat: float, lng: float, redis) -> tuple[float, int]:
    settings = get_settings()
    center = h3.latlng_to_cell(lat, lng, settings.H3_RESOLUTION_SEARCH)
    cells = h3.grid_disk(center, 1)

    async with redis.pipeline(transaction=False) as pipe:
        for cell in cells:
            pipe.smembers(f"h3:7:{cell}")
        results = await pipe.execute()

    all_detailers: set[str] = set()
    for members in results:
        all_detailers.update(members)

    active_count = 0
    if all_detailers:
        async with redis.pipeline(transaction=False) as pipe:
            for did in all_detailers:
                pipe.exists(f"active:{did}")
            flags = await pipe.execute()
        active_count = sum(flags)

    thresholds = sorted(settings.SURGE_THRESHOLDS, key=lambda t: t[0])
    multiplier = 1.0
    for max_count, mult in thresholds:
        if active_count <= max_count:
            multiplier = mult
            break

    return multiplier, active_count


def generate_fare_token(fare_id: str, price_cents: int, expires_at: datetime) -> str:
    settings = get_settings()
    msg = f"{fare_id}:{price_cents}:{expires_at.isoformat()}"
    return hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        msg.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_fare_token(
    token: str, fare_id: str, price_cents: int, expires_at: datetime
) -> bool:
    if datetime.now(timezone.utc) > expires_at:
        return False
    expected = generate_fare_token(fare_id, price_cents, expires_at)
    return hmac.compare_digest(expected, token)
