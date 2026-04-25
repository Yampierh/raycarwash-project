from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AppointmentStatus, AuditAction, Review
from app.repositories.appointment_repository import AppointmentRepository
from domains.audit.repository import AuditRepository
from domains.reviews.repository import ReviewRepository
from domains.reviews.schemas import ReviewCreate

logger = logging.getLogger(__name__)


class ReviewService:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._review_repo = ReviewRepository(db)
        self._appointment_repo = AppointmentRepository(db)
        self._audit_repo = AuditRepository(db)

    async def create_review(self, payload: ReviewCreate, reviewer_id: uuid.UUID) -> Review:
        """
        Submit a post-service review.

        Rules: appointment must be COMPLETED, reviewer must be the client,
        one review per appointment (unique constraint + application guard).
        """
        appointment = await self._appointment_repo.get_by_id(payload.appointment_id)
        if appointment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment {payload.appointment_id} not found.",
            )

        if appointment.status != AppointmentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Reviews can only be submitted for COMPLETED appointments. "
                    f"Current status: '{appointment.status.value}'."
                ),
            )

        if appointment.client_id != reviewer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the client who booked this appointment can leave a review.",
            )

        existing = await self._review_repo.get_by_appointment(payload.appointment_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A review for this appointment already exists.",
            )

        review = Review(
            appointment_id=payload.appointment_id,
            reviewer_id=reviewer_id,
            detailer_id=appointment.detailer_id,
            rating=payload.rating,
            comment=payload.comment,
        )
        created = await self._review_repo.create(review)
        await self._review_repo.update_detailer_aggregate(appointment.detailer_id, payload.rating)

        await self._audit_repo.log(
            action=AuditAction.REVIEW_CREATED,
            entity_type="review",
            entity_id=str(created.id),
            actor_id=reviewer_id,
            metadata={
                "appointment_id": str(payload.appointment_id),
                "detailer_id": str(appointment.detailer_id),
                "rating": payload.rating,
            },
        )

        logger.info(
            "Review created | id=%s appointment=%s detailer=%s rating=%d",
            created.id, payload.appointment_id, appointment.detailer_id, payload.rating,
        )
        return created
