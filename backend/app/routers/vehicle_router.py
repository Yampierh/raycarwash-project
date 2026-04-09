# app/routers/vehicle_router.py

from __future__ import annotations

import logging
import uuid # <--- Importante para el tipado del endpoint
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import User, Vehicle
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.schemas import VehicleCreate, VehicleRead
from app.services.auth import get_current_user
from app.services.vehicle_lookup import lookup_vin_data, map_body_to_size

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vehicles", tags=["Vehicles"])

@router.post(
    "",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un vehículo."
)
async def create_vehicle(
    payload: VehicleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VehicleRead:
    if not current_user.is_client():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Solo clientes pueden registrar vehículos.",
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
            detail=f"La placa '{payload.license_plate}' ya está registrada.",
        )
    return VehicleRead.model_validate(created)

@router.get("", response_model=list[VehicleRead])
async def list_my_vehicles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[VehicleRead]:
    vehicles = await VehicleRepository(db).get_by_owner(current_user.id)
    return [VehicleRead.model_validate(v) for v in vehicles]

@router.get("/lookup/{vin}")
async def get_vin_info(vin: str, current_user: User = Depends(get_current_user)):
    if len(vin) != 17:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El VIN debe tener 17 caracteres.",
        )
    return await lookup_vin_data(vin.upper())

@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: uuid.UUID, # El tipo UUID ya está definido arriba
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = VehicleRepository(db)
    success = await repo.soft_delete(vehicle_id=vehicle_id, owner_id=current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehículo no encontrado o no tienes permiso para borrarlo."
        )
    
    return None

@router.put("/{vehicle_id}", response_model=VehicleRead)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = VehicleRepository(db)
    
    # Convertimos el schema a diccionario para pasarlo como kwargs
    update_data = payload.model_dump()
    
    # El owner_id no debería cambiar, pero nos aseguramos
    updated_vehicle = await repo.update(
        vehicle_id=vehicle_id,
        owner_id=current_user.id,
        **update_data
    )
    
    if not updated_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehículo no encontrado o no tienes permiso para editarlo."
        )
        
    return VehicleRead.model_validate(updated_vehicle)