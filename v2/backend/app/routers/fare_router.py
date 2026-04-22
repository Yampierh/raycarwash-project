from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.redis import get_redis
from app.db.session import get_db
from app.services.auth import get_current_user
from app.services.fare_service import (
    calculate_estimated_price,
    calculate_surge,
    cache_fare,
    generate_fare_token,
)

router = APIRouter(prefix="/api/v2/fares", tags=["Fares"])
settings = get_settings()


# ------------------------------------------------------------------ #
#  Schemas                                                            #
# ------------------------------------------------------------------ #

class FareEstimateRequest(BaseModel):
    service_id: uuid.UUID
    vehicle_sizes: list[str] = Field(
        ...,
        description="List of vehicle sizes: small | medium | large | xl",
        min_length=1,
        max_length=10,
    )
    client_lat: float = Field(..., ge=-90,  le=90)
    client_lng: float = Field(..., ge=-180, le=180)
    addon_ids: list[uuid.UUID] = Field(default_factory=list)


class FareEstimateResponse(BaseModel):
    fare_id: uuid.UUID
    fare_token: str
    base_price_cents: int
    surge_multiplier: Decimal
    estimated_price_cents: int
    nearby_detailers_count: int
    expires_at: datetime
    expires_in_seconds: int


# ------------------------------------------------------------------ #
#  Endpoint                                                           #
# ------------------------------------------------------------------ #

@router.post(
    "/estimate",
    response_model=FareEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimate fare with real-time surge pricing.",
    description=(
        "Returns a signed fare_token that locks in the price for "
        f"{settings.FARE_TOKEN_TTL_SECONDS // 60} minutes. "
        "Pass fare_token when creating a ride request."
    ),
)
async def estimate_fare(
    payload: FareEstimateRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> FareEstimateResponse:
    from sqlalchemy import select
    from app.models.models import Service, Addon

    # Load service
    result = await db.execute(
        select(Service).where(
            Service.id == payload.service_id,
            Service.is_active.is_(True),
        )
    )
    service = result.scalar_one_or_none()
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SERVICE_NOT_FOUND", "message": "Service not found or inactive."},
        )

    # Load addons
    addon_price_cents = 0
    if payload.addon_ids:
        result = await db.execute(
            select(Addon).where(
                Addon.id.in_(payload.addon_ids),
                Addon.is_active.is_(True),
            )
        )
        addons = result.scalars().all()
        addon_price_cents = sum(a.price_cents for a in addons)

    # Calculate base price across vehicle sizes
    size_col = {
        "small":  service.price_small,
        "medium": service.price_medium,
        "large":  service.price_large,
        "xl":     service.price_xl,
    }
    base_price_cents = sum(
        size_col.get(size, service.base_price_cents)
        for size in payload.vehicle_sizes
    ) + addon_price_cents

    # Surge pricing via H3 k-ring
    surge_multiplier, nearby_count = await calculate_surge(
        redis_client,
        payload.client_lat,
        payload.client_lng,
    )

    estimated_price_cents = calculate_estimated_price(base_price_cents, surge_multiplier)

    # Build fare
    fare_id    = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.FARE_TOKEN_TTL_SECONDS)
    fare_token = generate_fare_token(str(fare_id), estimated_price_cents, expires_at)

    fare_data = {
        "fare_id":               str(fare_id),
        "client_id":             str(current_user.id),
        "service_id":            str(payload.service_id),
        "vehicle_sizes":         payload.vehicle_sizes,
        "addon_ids":             [str(a) for a in payload.addon_ids],
        "client_lat":            payload.client_lat,
        "client_lng":            payload.client_lng,
        "base_price_cents":      base_price_cents,
        "surge_multiplier":      str(surge_multiplier),
        "estimated_price_cents": estimated_price_cents,
        "nearby_detailers_count": nearby_count,
        "expires_at":            expires_at.isoformat(),
        "fare_token":            fare_token,
    }
    await cache_fare(redis_client, str(fare_id), fare_data)

    return FareEstimateResponse(
        fare_id=fare_id,
        fare_token=fare_token,
        base_price_cents=base_price_cents,
        surge_multiplier=surge_multiplier,
        estimated_price_cents=estimated_price_cents,
        nearby_detailers_count=nearby_count,
        expires_at=expires_at,
        expires_in_seconds=settings.FARE_TOKEN_TTL_SECONDS,
    )
