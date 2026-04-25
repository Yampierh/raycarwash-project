from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from infrastructure.nhtsa.client import lookup_vin_data
from app.models.models import User, Vehicle
from app.services.auth import get_current_user
from domains.vehicles.repository import VehicleRepository
from domains.vehicles.schemas import VehicleCreate, VehicleRead

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
