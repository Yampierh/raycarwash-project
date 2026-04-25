from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.users.models import User
from domains.auth.service import get_current_user
from domains.reviews.repository import ReviewRepository
from domains.reviews.service import ReviewService
from domains.reviews.schemas import ReviewCreate, ReviewRead
from shared.schemas import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reviews", tags=["Reviews"])


@router.post(
    "",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a review for a completed appointment.",
    responses={
        403: {"description": "Not the client on this appointment."},
        409: {"description": "Review already exists for this appointment."},
        422: {"description": "Appointment is not COMPLETED."},
    },
)
async def create_review(
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRead:
    svc = ReviewService(db)
    review = await svc.create_review(payload=payload, reviewer_id=current_user.id)
    return ReviewRead.model_validate(review)


@router.get(
    "/detailer/{detailer_id}",
    response_model=dict,
    summary="Paginated list of reviews for a detailer.",
)
async def list_detailer_reviews(
    detailer_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Public endpoint — no authentication required."""
    repo = ReviewRepository(db)
    offset = (page - 1) * page_size
    items, total = await repo.get_by_detailer(
        detailer_id=detailer_id, offset=offset, limit=page_size
    )
    return PaginatedResponse.build(
        items=[ReviewRead.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    ).model_dump()
