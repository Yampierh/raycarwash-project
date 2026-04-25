from __future__ import annotations

import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.audit.models import AuditAction, AuditLog


class AuditRepository:
    """
    Append-only audit log store. Only INSERT and SELECT — never UPDATE or DELETE.
    Immutability enforced at application layer as defence-in-depth.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        actor_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            stripe_metadata=metadata,
        )
        self._db.add(entry)
        await self._db.flush()
        return entry

    async def get_for_entity(self, entity_type: str, entity_id: str) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id == entity_id,
                )
            )
            .order_by(AuditLog.created_at.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
