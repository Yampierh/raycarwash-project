from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from infrastructure.db.session import get_db
from infrastructure.nhtsa.client import (
    SIZE_LABEL,
    estimate_size_from_make_model,
    lookup_vin_data,
)
from domains.services_catalog.models import Service, ServiceCategory
from domains.users.models import User
from domains.vehicles.models import Vehicle, VehicleSize
from domains.auth.service import get_current_user
from domains.vehicles.repository import VehicleRepository
from domains.vehicles.schemas import (
    PriceEstimateTier,
    VehicleCreate,
    VehiclePriceEstimateResponse,
    VehicleRead,
)
from shared.schemas import Envelope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vehicles", tags=["Vehicles"])


@router.post(
    "",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new vehicle for the authenticated client.",
    responses={
        403: {"description": "Only clients can register vehicles."},
        409: {"description": "License plate already registered."},
    },
)
async def create_vehicle(
    payload: VehicleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VehicleRead:
    if not current_user.is_client():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can register vehicles.",
        )
    vehicle = Vehicle(
        owner_id=current_user.id,
        make=payload.make,
        model=payload.model,
        year=payload.year,
        vin=payload.vin,
        series=payload.series,
        body_class=payload.body_class,
        color=payload.color,
        license_plate=payload.license_plate,
        notes=payload.notes,
    )
    try:
        created = await VehicleRepository(db).create(vehicle)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"License plate '{payload.license_plate}' is already registered.",
        )
    return VehicleRead.model_validate(created)


@router.get(
    "",
    response_model=list[VehicleRead],
    summary="List all vehicles owned by the authenticated client.",
)
async def list_my_vehicles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[VehicleRead]:
    vehicles = await VehicleRepository(db).get_by_owner(current_user.id)
    return [VehicleRead.model_validate(v) for v in vehicles]


# Service columns used by the price-estimate, in priority order
# (basic_wash anchor first, then full_detail). Hard-coded by category
# because the design only surfaces those two tiers on the signup card.
_PRICE_COLUMN_BY_SIZE: dict[VehicleSize, str] = {
    VehicleSize.SMALL:  "price_small",
    VehicleSize.MEDIUM: "price_medium",
    VehicleSize.LARGE:  "price_large",
    VehicleSize.XL:     "price_xl",
}
_DURATION_COLUMN_BY_SIZE: dict[VehicleSize, str] = {
    VehicleSize.SMALL:  "duration_small_minutes",
    VehicleSize.MEDIUM: "duration_medium_minutes",
    VehicleSize.LARGE:  "duration_large_minutes",
    VehicleSize.XL:     "duration_xl_minutes",
}


@router.get(
    "/price-estimate",
    response_model=Envelope[VehiclePriceEstimateResponse],
    summary=(
        "Anonymous price preview for the customer signup vehicle "
        "step. Approximates VehicleSize from year/make/model + returns "
        "prices for two anchor services (basic_wash + full_detail)."
    ),
)
@limiter.limit("30/minute")
async def price_estimate(
    request: Request,
    response: Response,
    year: int = Query(..., ge=1970, le=2030),
    make: str = Query(..., min_length=1, max_length=60),
    model: str = Query(..., min_length=1, max_length=60),
    db: AsyncSession = Depends(get_db),
) -> Envelope[VehiclePriceEstimateResponse]:
    """Plan 24 §3 C-1. Anonymous (no auth) — public during customer
    signup. The frontend calls this after Step 3 (vehicle entry) to
    show the "Mid-size SUV · Full detail $179 · Express wash $49"
    preview before the user commits to creating an account.
    """
    size = estimate_size_from_make_model(make, model)
    price_col = _PRICE_COLUMN_BY_SIZE[size]
    dur_col = _DURATION_COLUMN_BY_SIZE[size]

    # Cheapest service per anchor category. Picks deterministically
    # based on `base_price_cents` so the choice stays stable as the
    # catalog grows.
    tiers: list[PriceEstimateTier] = []
    for category in (ServiceCategory.BASIC_WASH, ServiceCategory.FULL_DETAIL):
        svc = (await db.execute(
            select(Service)
            .where(Service.category == category)
            .order_by(Service.base_price_cents.asc())
            .limit(1)
        )).scalar_one_or_none()
        if svc is None:
            continue
        tiers.append(PriceEstimateTier(
            name=svc.name,
            category=category.value,
            price_cents=getattr(svc, price_col),
            duration_minutes=getattr(svc, dur_col),
        ))

    # Cache-Control: prices change rarely and this endpoint runs
    # before auth — heavy caching is safe.
    response.headers["Cache-Control"] = (
        "public, max-age=3600, stale-while-revalidate=300"
    )

    return Envelope(data=VehiclePriceEstimateResponse(
        year=year,
        make=make,
        model=model,
        estimated_size=size.value,
        size_label=SIZE_LABEL[size],
        tiers=tiers,
    ))


@router.get(
    "/lookup/{vin}",
    summary="Decode VIN via NHTSA API.",
    responses={
        400: {"description": "VIN must be exactly 17 characters."},
        404: {"description": "Vehicle not found in NHTSA database."},
    },
)
async def get_vin_info(vin: str, current_user: User = Depends(get_current_user)):
    if len(vin) != 17:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VIN must be exactly 17 characters.",
        )
    return await lookup_vin_data(vin.upper())


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a vehicle.",
)
async def delete_vehicle(
    vehicle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    success = await VehicleRepository(db).soft_delete(
        vehicle_id=vehicle_id, owner_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found or you don't have permission to delete it.",
        )
    return None


@router.put(
    "/{vehicle_id}",
    response_model=VehicleRead,
    summary="Update vehicle details.",
    responses={409: {"description": "License plate already in use."}},
)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated_vehicle = await VehicleRepository(db).update(
        vehicle_id=vehicle_id,
        owner_id=current_user.id,
        **payload.model_dump(),
    )
    if not updated_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found or you don't have permission to edit it.",
        )
    return VehicleRead.model_validate(updated_vehicle)
