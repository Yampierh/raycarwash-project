from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.payments.models import FareEstimate
from domains.services_catalog.models import Service
from domains.vehicles.models import VehicleSize
from domains.payments.schemas import FareEstimateRequest, FareEstimateResponse
from domains.auth.service import require_role
from app.services.fare_service import calculate_surge, generate_fare_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fares", tags=["Fares"])

FARE_TTL_SECONDS = 900  # 15 minutes

_SIZE_FIELD = {
    VehicleSize.SMALL:  "price_small",
    VehicleSize.MEDIUM: "price_medium",
    VehicleSize.LARGE:  "price_large",
    VehicleSize.XL:     "price_xl",
}


@router.post(
    "/estimate",
    response_model=FareEstimateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Estimate fare with surge pricing for a service.",
)
async def estimate_fare(
    payload: FareEstimateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("client")),
) -> FareEstimateResponse:
    # ---- Resolve service ----
    result = await db.execute(
        select(Service).where(Service.id == payload.service_id, Service.is_active.is_(True))
    )
    service = result.scalar_one_or_none()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")

    # ---- Base price: sum of size-specific prices for each vehicle ----
    base_price_cents = sum(
        getattr(service, _SIZE_FIELD[vs]) for vs in payload.vehicle_sizes
    )

    # ---- Surge pricing ----
    redis = request.app.state.redis
    surge_multiplier, nearby_count = await calculate_surge(
        payload.client_lat, payload.client_lng, redis
    )

    estimated_price_cents = math.ceil(base_price_cents * surge_multiplier)

    # ---- Build FareEstimate record ----
    fare_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=FARE_TTL_SECONDS)

    fare_token = generate_fare_token(str(fare_id), estimated_price_cents, expires_at)

    estimate = FareEstimate(
        id=fare_id,
        client_id=current_user.id,
        service_id=payload.service_id,
        vehicle_sizes=[vs.value for vs in payload.vehicle_sizes],
        client_lat=payload.client_lat,
        client_lng=payload.client_lng,
        base_price_cents=base_price_cents,
        surge_multiplier=surge_multiplier,
        estimated_price_cents=estimated_price_cents,
        nearby_detailers_count=nearby_count,
        fare_token=fare_token,
        expires_at=expires_at,
    )
    db.add(estimate)
    await db.commit()

    # ---- Cache in Redis ----
    cache_payload = json.dumps({
        "fare_id": str(fare_id),
        "client_id": str(current_user.id),
        "service_id": str(payload.service_id),
        "estimated_price_cents": estimated_price_cents,
        "expires_at": expires_at.isoformat(),
    })
    await redis.setex(f"fare:{fare_token}", FARE_TTL_SECONDS, cache_payload)

    logger.info(
        "FareEstimate created | id=%s surge=%.2f price=%d nearby=%d",
        fare_id, surge_multiplier, estimated_price_cents, nearby_count,
    )

    return FareEstimateResponse(
        fare_token=fare_token,
        base_price_cents=base_price_cents,
        surge_multiplier=surge_multiplier,
        estimated_price_cents=estimated_price_cents,
        nearby_detailers_count=nearby_count,
        expires_at=expires_at,
    )
