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

    async def update_detailer_aggregate(self, detailer_id: uuid.UUID) -> None:
        """
        Recompute and store the detailer's average rating and review count
        directly in their DetailerProfile.

        WHY denormalise here?
        Every public-facing detailer list query would otherwise require
        a GROUP BY + AVG subquery. Denormalising into DetailerProfile
        makes reads O(1) while writes (new review → update aggregate) are
        rare. The trade-off is strongly in favour of the read-heavy pattern.
        """
        agg_stmt = select(
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("total"),
        ).where(
            Review.detailer_id == detailer_id,
            Review.is_deleted.is_(False),
        )
        agg_result = await self._db.execute(agg_stmt)
        row = agg_result.one()

        await self._db.execute(
            update(DetailerProfile)
            .where(DetailerProfile.user_id == detailer_id)
            .values(
                average_rating=round(float(row.avg_rating), 2) if row.avg_rating else None,
                total_reviews=row.total,
            )
        )
        await self._db.flush()