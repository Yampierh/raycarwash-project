"""
domains/auth/session_repository.py — Plan 23 Fase 1 día 2.

Stateful session CRUD backing the `sid` claim on access tokens. Combined
with the Redis cache in service.py this gives us real-time revocation +
device listing without paying a DB hop on every request.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import Session


class SessionRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── CRUD ───────────────────────────────────────────────────────── #

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        family_id: uuid.UUID,
        device_name: str | None = None,
        device_type: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Session:
        session = Session(
            user_id=user_id,
            family_id=family_id,
            device_name=device_name,
            device_type=device_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._db.add(session)
        await self._db.flush()
        await self._db.refresh(session)
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        stmt = select(Session).where(Session.id == session_id)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def get_by_family(self, family_id: uuid.UUID) -> Session | None:
        """Return the active session for a refresh-token family. There is
        only one (NULL revoked) row per family by design."""
        stmt = (
            select(Session)
            .where(Session.family_id == family_id, Session.revoked.is_(False))
            .order_by(Session.created_at.desc())
            .limit(1)
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def revoke(self, session_id: uuid.UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Session)
            .where(Session.id == session_id, Session.revoked.is_(False))
            .values(revoked=True, revoked_at=now)
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.revoked.is_(False))
            .values(revoked=True, revoked_at=now)
        )
        result = await self._db.execute(stmt)
        return result.rowcount

    async def update_last_active(
        self,
        session_id: uuid.UUID,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Refresh `last_active_at` (and optionally IP/UA). Callers throttle
        this via Redis to avoid a write per request."""
        now = datetime.now(timezone.utc)
        values: dict = {"last_active_at": now}
        if ip_address is not None:
            values["ip_address"] = ip_address
        if user_agent is not None:
            values["user_agent"] = user_agent
        stmt = update(Session).where(Session.id == session_id).values(**values)
        await self._db.execute(stmt)

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
        include_revoked: bool = False,
    ) -> tuple[list[Session], int]:
        base = select(Session).where(Session.user_id == user_id)
        if not include_revoked:
            base = base.where(Session.revoked.is_(False))

        total = (await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )).scalar_one()

        stmt = (
            base
            .order_by(Session.last_active_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self._db.execute(stmt)).scalars().all())
        return rows, total

    async def delete_expired(self, days: int = 30) -> int:
        """Purge revoked sessions older than N days. Returns # deleted.
        Intended for the cleanup worker (Plan 23 Fase 8)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        from sqlalchemy import delete
        stmt = delete(Session).where(
            Session.revoked.is_(True),
            Session.revoked_at < cutoff,
        )
        return (await self._db.execute(stmt)).rowcount
