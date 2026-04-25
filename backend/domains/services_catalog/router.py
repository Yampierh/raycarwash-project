from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.services_catalog.repository import AddonRepository, ServiceRepository
from domains.services_catalog.schemas import AddonRead, ServiceRead

logger = logging.getLogger(__name__)

# ── Services catalogue ─────────────────────────────────────────────── #

router = APIRouter(prefix="/api/v1/services", tags=["Services"])


@router.get(
    "",
    response_model=list[ServiceRead],
    summary="List all active detailing services with per-size pricing.",
)
async def list_services(db: AsyncSession = Depends(get_db)) -> list[ServiceRead]:
    """Public — no auth. Returns catalogue ordered by base price ascending."""
    repo = ServiceRepository(db)
    services = await repo.get_all_active()
    if not services:
        logger.warning("Service catalogue is empty — seed may not have run.")
    return [ServiceRead.model_validate(s) for s in services]


@router.get(
    "/{service_id}",
    response_model=ServiceRead,
    responses={404: {"description": "Service not found or inactive."}},
    summary="Retrieve a specific service by UUID.",
)
async def get_service(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ServiceRead:
    service = await ServiceRepository(db).get_by_id(service_id)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_id}' not found or is no longer active.",
        )
    return ServiceRead.model_validate(service)


# ── Addons catalogue ────────────────────────────────────────────────── #

addon_router = APIRouter(prefix="/api/v1/addons", tags=["Addons"])


@addon_router.get(
    "",
    response_model=list[AddonRead],
    summary="List all active optional add-on services.",
)
async def list_addons(db: AsyncSession = Depends(get_db)) -> list[AddonRead]:
    """Public — no auth. Returns addons sorted alphabetically."""
    addons = await AddonRepository(db).list_active()
    return [AddonRead.model_validate(a) for a in addons]
