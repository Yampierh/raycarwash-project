# app/repositories/audit_repository.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditAction, AuditLog


class AuditRepository:
    """
    Append-only audit log store.

    Methods here only INSERT and SELECT — never UPDATE or DELETE.
    Ensuring immutability at the application layer is a defence-in-depth
    measure on top of the DB-level INSERT-only privilege policy.
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
        """
        Append a single audit event.

        Fire-and-forget from the service layer — callers should NOT
        await this if they want non-blocking logging. In Sprint 4,
        move to a background task queue (Celery / ARQ) to decouple
        audit writes from the request path entirely.
        """
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )
        self._db.add(entry)
        await self._db.flush()
        return entry

    async def get_for_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> list[AuditLog]:
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