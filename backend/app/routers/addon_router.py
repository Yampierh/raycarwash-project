# app/routers/addon_router.py  —  Sprint 5
#
# GET /api/v1/addons — public catalogue of optional extras.
# No auth required; clients browse addons before logging in.

from __future__ import annotations

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.addon_repository import AddonRepository
from app.schemas.schemas import AddonRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/addons", tags=["Addons"])


@router.get(
    "",
    response_model=list[AddonRead],
    summary="List all active optional add-on services.",
    description="""
    Returns the full catalogue of active addons sorted by name.
    
    Addons are optional extras that can be added to a service booking:
    - Clay Bar Treatment
    - Odor Eliminator
    - Ceramic Spray Coat
    - etc.
    
    Their price_cents and duration_minutes are added to the appointment totals.
    
    This endpoint is public (no authentication required) so clients can
    browse available add-ons before registering.
    """,
    responses={
        200: {"description": "List of active add-ons."},
    },
)
async def list_addons(
    db: AsyncSession = Depends(get_db),
) -> list[AddonRead]:
    """
    List all active add-ons.
    
    Returns only add-ons where is_active=True and is_deleted=False.
    Sorted alphabetically by name.
    """
    addons = await AddonRepository(db).list_active()
    return [AddonRead.model_validate(a) for a in addons]
