# app/routers/addon_router.py  —  Sprint 5
#
# GET /api/v1/addons — public catalogue of optional extras.
# No auth required; clients browse addons before logging in.

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.addon_repository import AddonRepository
from app.schemas.schemas import AddonRead

router = APIRouter(prefix="/api/v1/addons", tags=["Addons"])


@router.get(
    "",
    response_model=list[AddonRead],
    summary="List all active optional add-on services.",
)
async def list_addons(
    db: AsyncSession = Depends(get_db),
) -> list[AddonRead]:
    """
    Returns the full catalogue of active addons sorted by name.

    Addons are stacked on top of the base service at booking time.
    Their price_cents and duration_minutes are summed into the appointment totals.
    """
    addons = await AddonRepository(db).list_active()
    return [AddonRead.model_validate(a) for a in addons]
