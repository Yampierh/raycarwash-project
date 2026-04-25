"""
infrastructure/h3/client.py

H3 geospatial helpers: candidate cell lookup and detailer index maintenance.
Single source of truth — never duplicate these functions in domain code.
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import h3
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings


def get_candidate_cells(lat: float, lng: float, radius_miles: float) -> set[str]:
    """grid_disk at resolution 7. H3 R7 avg edge ≈ 1.22 km ≈ 0.76 miles."""
    center = h3.latlng_to_cell(lat, lng, 7)
    k = max(1, math.ceil(radius_miles / 0.76))
    return h3.grid_disk(center, k)


async def find_nearby_detailers(
    lat: float, lng: float, radius_miles: float, redis
) -> set[str]:
    """Return set of detailer_id strings that are currently active near (lat, lng)."""
    cells = get_candidate_cells(lat, lng, radius_miles)

    async with redis.pipeline(transaction=False) as pipe:
        for cell in cells:
            pipe.smembers(f"h3:7:{cell}")
        results = await pipe.execute()

    all_detailers: set[str] = set()
    for members in results:
        all_detailers.update(members)

    if not all_detailers:
        return set()

    async with redis.pipeline(transaction=False) as pipe:
        for did in all_detailers:
            pipe.exists(f"active:{did}")
        active_flags = await pipe.execute()

    return {did for did, active in zip(all_detailers, active_flags) if active}


async def update_h3_index(
    detailer_id: str,
    new_lat: float,
    new_lng: float,
    old_lat: float | None,
    old_lng: float | None,
    redis,
    db: AsyncSession,
) -> None:
    """Update Redis H3 sets and persist index columns to PostgreSQL."""
    from app.models.models import ProviderProfile

    settings = get_settings()
    new_cell_r7 = h3.latlng_to_cell(new_lat, new_lng, settings.H3_RESOLUTION_SEARCH)
    new_cell_r9 = h3.latlng_to_cell(new_lat, new_lng, settings.H3_RESOLUTION_STORE)

    if old_lat is not None and old_lng is not None:
        old_cell_r7 = h3.latlng_to_cell(old_lat, old_lng, settings.H3_RESOLUTION_SEARCH)
        if old_cell_r7 != new_cell_r7:
            await redis.srem(f"h3:7:{old_cell_r7}", detailer_id)

    await redis.sadd(f"h3:7:{new_cell_r7}", detailer_id)
    await redis.setex(
        f"active:{detailer_id}", settings.DETAILER_ACTIVE_TTL_SECONDS, "1"
    )

    await db.execute(
        update(ProviderProfile)
        .where(ProviderProfile.user_id == uuid.UUID(detailer_id))
        .values(
            current_lat=new_lat,
            current_lng=new_lng,
            h3_index_r7=new_cell_r7,
            h3_index_r9=new_cell_r9,
            last_location_update=datetime.now(timezone.utc),
        )
    )
    await db.commit()
