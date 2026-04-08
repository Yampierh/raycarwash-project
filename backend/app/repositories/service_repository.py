# app/repositories/service_repository.py

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Service


class ServiceRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, service_id: uuid.UUID) -> Service | None:
        """Return an active (non-deleted, is_active) service by PK."""
        stmt = select(Service).where(
            Service.id == service_id,
            Service.is_active.is_(True),
            Service.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> list[Service]:
        stmt = (
            select(Service)
            .where(
                Service.is_active.is_(True),
                Service.is_deleted.is_(False),
            )
            .order_by(Service.base_price_cents.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())