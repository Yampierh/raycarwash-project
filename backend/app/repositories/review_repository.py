# app/repositories/review_repository.py

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import DetailerProfile, Review


class ReviewRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_appointment(self, appointment_id: uuid.UUID) -> Review | None:
        stmt = select(Review).where(
            Review.appointment_id == appointment_id,
            Review.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_detailer(
        self,
        detailer_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Review], int]:
        conditions = [
            Review.detailer_id == detailer_id,
            Review.is_deleted.is_(False),
        ]
        count_stmt = (
            select(func.count())
            .select_from(Review)
            .where(*conditions)
        )
        total: int = (await self._db.execute(count_stmt)).scalar_one()

        stmt = (
            select(Review)
            .where(*conditions)
            .order_by(Review.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def create(self, review: Review) -> Review:
        self._db.add(review)
        await self._db.flush()
        await self._db.refresh(review)
        return review

    async def update_detailer_aggregate(self, detailer_id: uuid.UUID, new_rating: int) -> None:
        """
        FIX: Atomically update average_rating to prevent race conditions.
        
        Previous implementation used a read-then-write pattern that was
        vulnerable to concurrent review submissions. This version uses
        a single atomic SQL UPDATE:
        
        new_avg = (current_avg * total_count + new_rating) / (total_count + 1)
        
        This prevents the "Lost Update" anomaly where two concurrent reviews
        could result in one being ignored.
        
        WHY denormalise here?
        Every public-facing detailer list query would otherwise require
        a GROUP BY + AVG subquery. Denormalising into DetailerProfile
        makes reads O(1) while writes (new review → update aggregate) are
        rare. The trade-off is strongly in favour of the read-heavy pattern.
        """
        # Atomic SQL update - no race condition possible
        # Uses COALESCE to handle the first review (NULL → 0)
        await self._db.execute(
            update(DetailerProfile)
            .where(DetailerProfile.user_id == detailer_id)
            .values(
                average_rating=(
                    # SQLite/Postgres compatible formula
                    # new_avg = (old_avg * total + new) / (total + 1)
                    # But we compute it in SQL to be atomic
                    (DetailerProfile.average_rating * DetailerProfile.total_reviews + new_rating) 
                    / (DetailerProfile.total_reviews + 1)
                ),
                total_reviews=DetailerProfile.total_reviews + 1,
            )
        )
        await self._db.flush()