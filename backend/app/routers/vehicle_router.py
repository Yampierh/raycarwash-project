# app/routers/vehicle_router.py

"""
Vehicle Management Router

Provides endpoints for vehicle CRUD operations.
All endpoints require client authentication.
"""

from __future__ import annotations

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import User, Vehicle
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.schemas import VehicleCreate, VehicleRead
from app.services.auth import get_current_user
from app.services.vehicle_lookup import lookup_vin_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vehicles", tags=["Vehicles"])


@router.post(
    "",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new vehicle for the authenticated client.",
    description="""
    Register a vehicle owned by the authenticated client.
    
    The vehicle VIN will be decoded via NHTSA API if provided,
    extracting make, model, year, series, and body_class.
    
    Body class determines the vehicle size used for pricing:
    - small: Sedan, Coupe
    - medium: SUV, Crossover
    - medium: Pickup (single cab)
    - large: Crew Cab Pickup
    - xl: Van, Sprinter
    """,
    responses={
        201: {"description": "Vehicle created successfully."},
        400: {"description": "Invalid vehicle data."},
        401: {"description": "Not authenticated."},
        403: {"description": "Only clients can register vehicles."},
        409: {"description": "License plate already registered."},
    },
)
async def create_vehicle(
    payload: VehicleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VehicleRead:
    """
    Register a new vehicle for the authenticated client.
    
    The owner_id is automatically extracted from the JWT token,
    preventing IDOR attacks.
    """
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
    description="Returns all active (non-deleted) vehicles belonging to the authenticated user.",
    responses={
        200: {"description": "List of vehicles."},
        401: {"description": "Not authenticated."},
    },
)
async def list_my_vehicles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[VehicleRead]:
    """
    List all vehicles owned by the authenticated client.
    
    Results are sorted by creation date (newest first).
    Soft-deleted vehicles are automatically filtered out.
    """
    vehicles = await VehicleRepository(db).get_by_owner(current_user.id)
    return [VehicleRead.model_validate(v) for v in vehicles]


@router.get(
    "/lookup/{vin}",
    summary="Decode VIN via NHTSA API.",
    description="""
    Lookup vehicle information using the National Highway Traffic Safety Administration (NHTSA) API.
    
    Returns: make, model, year, series, body_class.
    The body_class is used to determine vehicle size for pricing calculations.
    """,
    responses={
        200: {"description": "VIN decoded successfully."},
        400: {"description": "VIN must be exactly 17 characters."},
        401: {"description": "Not authenticated."},
        404: {"description": "Vehicle not found in NHTSA database."},
        422: {"description": "Invalid VIN format."},
    },
)
async def get_vin_info(vin: str, current_user: User = Depends(get_current_user)):
    """
    Decode a VIN to get vehicle details from NHTSA.
    
    The VIN must be exactly 17 characters (17-digit VIN).
    Returns a dictionary with make, model, year, series, and body_class.
    """
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
    description="Marks the vehicle as deleted (is_deleted=True). The vehicle data is preserved in the database.",
    responses={
        204: {"description": "Vehicle deleted successfully."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not the vehicle owner."},
        404: {"description": "Vehicle not found."},
    },
)
async def delete_vehicle(
    vehicle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft-delete a vehicle owned by the authenticated client.
    
    Only the vehicle owner can delete their own vehicle.
    The vehicle is not physically removed; is_deleted is set to True.
    """
    repo = VehicleRepository(db)
    success = await repo.soft_delete(vehicle_id=vehicle_id, owner_id=current_user.id)

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
    description="Update one or more fields of an existing vehicle. The license_plate cannot be changed to an existing one.",
    responses={
        200: {"description": "Vehicle updated successfully."},
        400: {"description": "Invalid vehicle data."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not the vehicle owner."},
        404: {"description": "Vehicle not found."},
        409: {"description": "License plate already in use."},
    },
)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update vehicle details.
    
    Only the vehicle owner can update their vehicle.
    All fields are optional - only provided fields will be updated.
    """
    repo = VehicleRepository(db)

    update_data = payload.model_dump()

    updated_vehicle = await repo.update(
        vehicle_id=vehicle_id,
        owner_id=current_user.id,
        **update_data,
    )

    if not updated_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found or you don't have permission to edit it.",
        )

    return VehicleRead.model_validate(updated_vehicle)