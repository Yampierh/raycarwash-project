from __future__ import annotations

import hashlib
import hmac
import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.services.h3_service import find_nearby_detailers

settings = get_settings()

# ------------------------------------------------------------------ #
#  Surge pricing                                                      #
# ------------------------------------------------------------------ #

async def calculate_surge(
    redis_client: aioredis.Redis,
    lat: float,
    lng: float,
) -> tuple[Decimal, int]:
    """
    Compute surge multiplier and active detailer count for a given location.

    Uses H3 k-ring search within SURGE_SEARCH_RADIUS_MILES. The multiplier
    is determined by the number of available detailers:

        < SURGE_TIER_CRITICAL_MAX  → SURGE_TIER_CRITICAL_MULT (e.g. 2.0×)
        < SURGE_TIER_HIGH_MAX      → SURGE_TIER_HIGH_MULT     (e.g. 1.5×)
        < SURGE_TIER_MODERATE_MAX  → SURGE_TIER_MODERATE_MULT (e.g. 1.2×)
        otherwise                  → 1.0× (no surge)

    Returns: (surge_multiplier, nearby_detailer_count)
    """
    detailer_ids = await find_nearby_detailers(
        redis_client,
        lat,
        lng,
        settings.SURGE_SEARCH_RADIUS_MILES,
    )
    count = len(detailer_ids)

    if count < settings.SURGE_TIER_CRITICAL_MAX:
        multiplier = Decimal(str(settings.SURGE_TIER_CRITICAL_MULT))
    elif count < settings.SURGE_TIER_HIGH_MAX:
        multiplier = Decimal(str(settings.SURGE_TIER_HIGH_MULT))
    elif count < settings.SURGE_TIER_MODERATE_MAX:
        multiplier = Decimal(str(settings.SURGE_TIER_MODERATE_MULT))
    else:
        multiplier = Decimal("1.0")

    return multiplier, count


# ------------------------------------------------------------------ #
#  Price calculation                                                  #
# ------------------------------------------------------------------ #

def calculate_estimated_price(
    base_price_cents: int,
    surge_multiplier: Decimal,
) -> int:
    """Apply surge to base price, always rounding up (ceil)."""
    return math.ceil(base_price_cents * float(surge_multiplier))


# ------------------------------------------------------------------ #
#  Fare token                                                         #
# ------------------------------------------------------------------ #

def _make_token_payload(fare_id: str, price_cents: int, expires_at: datetime) -> str:
    return f"{fare_id}:{price_cents}:{expires_at.isoformat()}"


def generate_fare_token(fare_id: str, price_cents: int, expires_at: datetime) -> str:
    """
    HMAC-SHA256 signed fare token.

    Prevents clients from manipulating the price between the estimate
    and the booking request. The token is short-lived (FARE_TOKEN_TTL_SECONDS).
    """
    payload = _make_token_payload(fare_id, price_cents, expires_at)
    return hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_fare_token(
    fare_id: str,
    price_cents: int,
    expires_at: datetime,
    provided_token: str,
) -> bool:
    expected = generate_fare_token(fare_id, price_cents, expires_at)
    return hmac.compare_digest(expected, provided_token)


# ------------------------------------------------------------------ #
#  Redis fare cache                                                   #
# ------------------------------------------------------------------ #

async def cache_fare(redis_client: aioredis.Redis, fare_id: str, fare_data: dict) -> None:
    await redis_client.set(
        f"fare:{fare_id}",
        json.dumps(fare_data),
        ex=settings.FARE_TOKEN_TTL_SECONDS,
    )


async def get_cached_fare(redis_client: aioredis.Redis, fare_id: str) -> dict | None:
    raw = await redis_client.get(f"fare:{fare_id}")
    if raw is None:
        return None
    return json.loads(raw)


async def invalidate_fare(redis_client: aioredis.Redis, fare_id: str) -> None:
    """Mark a fare as consumed so it cannot be reused."""
    await redis_client.delete(f"fare:{fare_id}")
