from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.redis import get_redis
from app.db.session import get_db
from app.services.assignment_service import signal_response
from app.services.auth import get_current_user
from app.services.fare_service import get_cached_fare, invalidate_fare, verify_fare_token

router = APIRouter(prefix="/api/v2/rides", tags=["Rides"])
settings = get_settings()


# ------------------------------------------------------------------ #
#  Schemas                                                            #
# ------------------------------------------------------------------ #

class RideRequest(BaseModel):
    fare_token: str
    mode: str = "asap"                 # "asap" | "scheduled"
    preferred_time: datetime | None = None  # ISO8601, required if mode=scheduled
    client_lat: float
    client_lng: float


class RideRequestResponse(BaseModel):
    appointment_id: uuid.UUID
    status: str
    estimated_price_cents: int
    surge_multiplier: float
    message: str


class RideActionResponse(BaseModel):
    appointment_id: uuid.UUID
    accepted: bool
    message: str


# ------------------------------------------------------------------ #
#  POST /rides/request — create ride from fare token                 #
# ------------------------------------------------------------------ #

@router.post(
    "/request",
    response_model=RideRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ride request. Triggers the assignment engine.",
)
async def request_ride(
    payload: RideRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> RideRequestResponse:
    # Resolve fare from Redis cache (the token maps to a cached fare_data dict)
    # The fare_token itself encodes the fare_id via the token payload convention.
    # We search by scanning the cache key pattern. In production, pass fare_id separately.
    # For simplicity here, the client sends the fare_token and we validate it.

    # Validate token structure and find fare data
    # NOTE: In production, have the client send both fare_id and fare_token.
    # Here we require the token and find the fare via a dedicated search.
    fare_data = await _resolve_fare_token(redis_client, payload.fare_token)
    if fare_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_FARE_TOKEN", "message": "Fare token is invalid or expired."},
        )

    fare_id              = fare_data["fare_id"]
    price_cents          = fare_data["estimated_price_cents"]
    surge_multiplier     = float(fare_data["surge_multiplier"])
    expires_at           = datetime.fromisoformat(fare_data["expires_at"])

    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FARE_EXPIRED", "message": "Fare estimate has expired. Please request a new one."},
        )

    if not verify_fare_token(fare_id, price_cents, expires_at, payload.fare_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_FARE_TOKEN", "message": "Fare token signature is invalid."},
        )

    # Consume the fare token (one-time use)
    await invalidate_fare(redis_client, fare_id)

    # Create appointment in SEARCHING status
    from app.models.models import Appointment, AppointmentStatus
    appointment = Appointment(
        id=uuid.uuid4(),
        client_id=current_user.id,
        detailer_id=None,
        service_id=uuid.UUID(fare_data["service_id"]),
        scheduled_time=payload.preferred_time or datetime.now(timezone.utc),
        estimated_end_time=datetime.now(timezone.utc),    # will be updated on assignment
        travel_buffer_end_time=datetime.now(timezone.utc),
        status=AppointmentStatus.SEARCHING,
        estimated_price=price_cents,
        service_latitude=payload.client_lat,
        service_longitude=payload.client_lng,
    )
    db.add(appointment)
    await db.flush()
    await db.refresh(appointment)
    appointment_id = str(appointment.id)
    await db.commit()

    # Publish to assignment queue (Redis Streams)
    await redis_client.xadd(
        "assignment_queue",
        {
            "appointment_id": appointment_id,
            "client_lat":     str(payload.client_lat),
            "client_lng":     str(payload.client_lng),
            "service_id":     fare_data["service_id"],
            "mode":           payload.mode,
            "preferred_time": payload.preferred_time.isoformat() if payload.preferred_time else "",
        },
        maxlen=1_000,
        approximate=True,
    )

    return RideRequestResponse(
        appointment_id=appointment.id,
        status="searching",
        estimated_price_cents=price_cents,
        surge_multiplier=surge_multiplier,
        message="We're finding the best available detailer for you.",
    )


# ------------------------------------------------------------------ #
#  PUT /rides/{id}/accept — detailer accepts an offer               #
# ------------------------------------------------------------------ #

@router.put(
    "/{appointment_id}/accept",
    response_model=RideActionResponse,
    summary="Detailer accepts an assignment offer.",
)
async def accept_ride(
    appointment_id: uuid.UUID,
    redis_client: aioredis.Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> RideActionResponse:
    if not current_user.is_detailer():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Detailers only.")

    await signal_response(redis_client, str(appointment_id), accepted=True)

    return RideActionResponse(
        appointment_id=appointment_id,
        accepted=True,
        message="Offer accepted. You have been assigned to this appointment.",
    )


# ------------------------------------------------------------------ #
#  PUT /rides/{id}/decline — detailer declines an offer             #
# ------------------------------------------------------------------ #

@router.put(
    "/{appointment_id}/decline",
    response_model=RideActionResponse,
    summary="Detailer declines an assignment offer.",
)
async def decline_ride(
    appointment_id: uuid.UUID,
    redis_client: aioredis.Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> RideActionResponse:
    if not current_user.is_detailer():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Detailers only.")

    await signal_response(redis_client, str(appointment_id), accepted=False)

    return RideActionResponse(
        appointment_id=appointment_id,
        accepted=False,
        message="Offer declined.",
    )


# ------------------------------------------------------------------ #
#  Internal helpers                                                   #
# ------------------------------------------------------------------ #

async def _resolve_fare_token(
    redis_client: aioredis.Redis,
    fare_token: str,
) -> dict | None:
    """
    Scan Redis for a fare whose stored token matches the provided one.

    In production, the client should send the fare_id alongside the token
    to allow O(1) lookup via GET fare:{fare_id}. This scan approach is
    acceptable during development.
    """
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match="fare:*", count=100)
        for key in keys:
            raw = await redis_client.get(key)
            if raw is None:
                continue
            import json
            data = json.loads(raw)
            if data.get("fare_token") == fare_token:
                return data
        if cursor == 0:
            break
    return None
