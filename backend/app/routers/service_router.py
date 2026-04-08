# app/routers/service_router.py
#
# Services are the "menu" of the marketplace — every client consults
# this list before booking. These endpoints are deliberately PUBLIC
# (no authentication required) because:
#   1. A potential client must see pricing before creating an account.
#   2. The data is read-only catalog data — no PII exposed.
#   3. Caching at the CDN level is straightforward for unauthenticated GETs.
#
# The per-size price columns (price_small … price_xl) are returned in
# the response so the frontend can instantly show the right price once
# the user selects their vehicle — without a round-trip to recalculate.

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.service_repository import ServiceRepository
from app.schemas.schemas import ServiceRead

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/services",
    tags=["Services"],
)

# ---- GET /  (full catalogue) ------------------------------------- #

@router.get(
    "",
    response_model=list[ServiceRead],
    summary="List all active detailing services with per-size pricing.",
    description=(
        "Returns the full service catalogue ordered by base price ascending. "
        "All price fields are in USD cents (divide by 100 for dollars). "
        "Use the `price_{size}` fields to display the correct price after "
        "the client selects their vehicle size."
    ),
)
async def list_services(
    db: AsyncSession = Depends(get_db),
) -> list[ServiceRead]:
    """
    Public endpoint — no authentication required.

    Pricing quick reference (base × size multiplier):
      small  ×1.0 | medium ×1.2 | large ×1.5 | xl ×2.0

    Example:
      Diamond Detail base = $250 (25,000 cents)
      GMC Sierra (XL)     = $250 × 2.0 = $500 (50,000 cents)
    """
    repo = ServiceRepository(db)
    services = await repo.get_all_active()

    if not services:
        logger.warning("Service catalogue is empty — seed may not have run.")

    logger.debug("Returning %d active services", len(services))
    return [ServiceRead.model_validate(s) for s in services]

# ---- GET /{id}  (single service) --------------------------------- #

@router.get(
    "/{service_id}",
    response_model=ServiceRead,
    summary="Retrieve a specific service by UUID.",
    responses={
        404: {"description": "Service not found or inactive."},
        422: {"description": "service_id is not a valid UUID."},
    },
)
async def get_service(
    service_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ServiceRead:
    """
    Fetch a single service by its UUID.

    Returns 404 for:
      - Services that do not exist.
      - Services that have been soft-deleted (is_deleted=True).
      - Services that have been deactivated (is_active=False).

    The frontend should call this endpoint to pre-populate the booking
    confirmation screen with up-to-date pricing after the user selects
    a service from the list.
    """
    repo = ServiceRepository(db)
    service = await repo.get_by_id(service_id)

    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_id}' not found or is no longer active.",
        )

    return ServiceRead.model_validate(service)