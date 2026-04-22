from __future__ import annotations

import asyncio
import logging
import math
from typing import TYPE_CHECKING

import h3
import redis.asyncio as aioredis

from app.core.config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
settings = get_settings()

# Redis key patterns
_H3_CELL_KEY = "h3:{resolution}:{cell}"  # SET of detailer_ids in this H3 cell
_ACTIVE_KEY  = "active:{detailer_id}"    # TTL sentinel — expires if detailer goes silent


# ------------------------------------------------------------------ #
#  Coordinate → H3 cell                                              #
# ------------------------------------------------------------------ #

def lat_lng_to_h3(lat: float, lng: float, resolution: int) -> str:
    return h3.geo_to_h3(lat, lng, resolution)


def h3_to_lat_lng(cell: str) -> tuple[float, float]:
    return h3.h3_to_geo(cell)  # returns (lat, lng)


# ------------------------------------------------------------------ #
#  K-ring search                                                      #
# ------------------------------------------------------------------ #

def get_candidate_cells(lat: float, lng: float, radius_miles: float) -> set[str]:
    """
    Return the set of H3 cells (at SEARCH resolution) covering the given radius.

    Uses h3.k_ring() which produces all cells within k steps of the center.
    Complexity: O(k²) cells — independent of how many detailers exist.
    """
    resolution = settings.H3_RESOLUTION_SEARCH
    center_cell = h3.geo_to_h3(lat, lng, resolution)
    k = max(1, round(radius_miles / settings.H3_MILES_PER_RING))
    return h3.k_ring(center_cell, k)


async def find_nearby_detailers(
    redis_client: aioredis.Redis,
    lat: float,
    lng: float,
    radius_miles: float = 25.0,
) -> set[str]:
    """
    Return detailer_id strings that are:
      1. In H3 cells covering the given radius
      2. Actively pinging (active:{id} key has not expired)

    Pipelining all SMEMBERS calls into one round-trip for efficiency.
    """
    cells = get_candidate_cells(lat, lng, radius_miles)

    pipeline = redis_client.pipeline(transaction=False)
    for cell in cells:
        key = _H3_CELL_KEY.format(resolution=settings.H3_RESOLUTION_SEARCH, cell=cell)
        pipeline.smembers(key)
    results = await pipeline.execute()

    all_candidates: set[str] = set()
    for members in results:
        all_candidates |= members

    if not all_candidates:
        return set()

    # Filter: only detailers whose active TTL key still exists
    pipeline = redis_client.pipeline(transaction=False)
    for detailer_id in all_candidates:
        pipeline.exists(_ACTIVE_KEY.format(detailer_id=detailer_id))
    active_flags = await pipeline.execute()

    return {
        did for did, is_active in zip(all_candidates, active_flags)
        if is_active
    }


# ------------------------------------------------------------------ #
#  H3 index update                                                    #
# ------------------------------------------------------------------ #

async def update_h3_index(
    redis_client: aioredis.Redis,
    detailer_id: str,
    new_lat: float,
    new_lng: float,
    old_lat: float | None = None,
    old_lng: float | None = None,
) -> tuple[str, str]:
    """
    Update the Redis H3 index when a detailer's location changes.

    - Removes from old cell (if the resolution-7 cell changed)
    - Adds to new cell
    - Refreshes the active TTL sentinel

    Returns: (new_cell_r7, new_cell_r9) for persistence to PostgreSQL.
    """
    res_search = settings.H3_RESOLUTION_SEARCH  # 7
    res_store  = settings.H3_RESOLUTION_STORE   # 9

    new_cell_r7 = h3.geo_to_h3(new_lat, new_lng, res_search)
    new_cell_r9 = h3.geo_to_h3(new_lat, new_lng, res_store)

    pipeline = redis_client.pipeline(transaction=False)

    # Remove from old cell only if the cell actually changed
    if old_lat is not None and old_lng is not None:
        old_cell_r7 = h3.geo_to_h3(old_lat, old_lng, res_search)
        if old_cell_r7 != new_cell_r7:
            old_key = _H3_CELL_KEY.format(resolution=res_search, cell=old_cell_r7)
            pipeline.srem(old_key, detailer_id)

    new_key = _H3_CELL_KEY.format(resolution=res_search, cell=new_cell_r7)
    pipeline.sadd(new_key, detailer_id)
    pipeline.set(
        _ACTIVE_KEY.format(detailer_id=detailer_id),
        "1",
        ex=settings.DETAILER_ACTIVE_TTL_SECONDS,
    )

    await pipeline.execute()
    return new_cell_r7, new_cell_r9


async def remove_from_h3_index(
    redis_client: aioredis.Redis,
    detailer_id: str,
    lat: float,
    lng: float,
) -> None:
    """Remove a detailer from H3 index (e.g., when they go offline)."""
    cell = h3.geo_to_h3(lat, lng, settings.H3_RESOLUTION_SEARCH)
    key  = _H3_CELL_KEY.format(resolution=settings.H3_RESOLUTION_SEARCH, cell=cell)
    pipeline = redis_client.pipeline(transaction=False)
    pipeline.srem(key, detailer_id)
    pipeline.delete(_ACTIVE_KEY.format(detailer_id=detailer_id))
    await pipeline.execute()
