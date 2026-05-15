from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.audit.models import AuditAction, AuditLog

if TYPE_CHECKING:
    from app.middleware.audit_context import AuditContext


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
        *,
        old_value: dict | None = None,
        new_value: dict | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> AuditLog:
        """
        Append an audit entry. When `audit_ctx` is provided (typically from
        `request.state.audit_ctx`), ip_address, user_agent and request_id are
        captured automatically — services don't have to pass them manually.

        For old_value/new_value redact PII via the workers/audit_log_redactor
        at >90d (ADR-006).
        """
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata,
            old_value=old_value,
            new_value=new_value,
            ip_address=audit_ctx.ip_address if audit_ctx else None,
            user_agent=audit_ctx.user_agent if audit_ctx else None,
            request_id=audit_ctx.request_id if audit_ctx else None,
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
