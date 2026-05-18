"""
domains/users/address_repository.py — CRUD for `user_addresses` rows.

Only DB access lives here — geocoding, audit logging, and default-flipping
ORCHESTRATION live in AddressService. The repository's one piece of
"smart" code is `set_default_atomic`, which uses a single UPDATE to
clear the previous default and set the new one in one statement —
respecting the partial unique index that m_006 created
(`(user_id) WHERE is_default = TRUE AND is_deleted = FALSE`).
"""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import and_, case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domains.users.user_address import UserAddress


class AddressRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ─── Reads ──────────────────────────────────────────────────────────────

    async def list_active(self, user_id: uuid.UUID) -> Sequence[UserAddress]:
        """All non-deleted addresses for a user, newest first."""
        stmt = (
            select(UserAddress)
            .where(
                UserAddress.user_id == user_id,
                UserAddress.is_deleted.is_(False),
            )
            .order_by(UserAddress.created_at.desc())
        )
        return (await self._db.scalars(stmt)).all()

    async def get_by_id(
        self, user_id: uuid.UUID, address_id: uuid.UUID
    ) -> UserAddress | None:
        """Fetch one address scoped to user (returns None if cross-user
        attempt or soft-deleted)."""
        stmt = (
            select(UserAddress)
            .where(
                UserAddress.id == address_id,
                UserAddress.user_id == user_id,
                UserAddress.is_deleted.is_(False),
            )
        )
        return await self._db.scalar(stmt)

    async def get_default(self, user_id: uuid.UUID) -> UserAddress | None:
        stmt = (
            select(UserAddress)
            .where(
                UserAddress.user_id == user_id,
                UserAddress.is_default.is_(True),
                UserAddress.is_deleted.is_(False),
            )
        )
        return await self._db.scalar(stmt)

    async def count_active(self, user_id: uuid.UUID) -> int:
        rows = await self.list_active(user_id)
        return len(rows)

    # ─── Writes ─────────────────────────────────────────────────────────────

    def add(self, address: UserAddress) -> None:
        """Add without flush; caller is responsible for commit/flush
        boundary to keep the whole create-or-update flow atomic."""
        self._db.add(address)

    async def soft_delete(
        self, user_id: uuid.UUID, address_id: uuid.UUID, *, now
    ) -> bool:
        """Soft-delete returning True iff a row was actually flipped.
        Idempotent: deleting an already-deleted address is a no-op
        returning False."""
        stmt = (
            update(UserAddress)
            .where(
                UserAddress.id == address_id,
                UserAddress.user_id == user_id,
                UserAddress.is_deleted.is_(False),
            )
            .values(is_deleted=True, deleted_at=now, is_default=False)
        )
        result = await self._db.execute(stmt)
        return (result.rowcount or 0) > 0

    async def set_default_atomic(
        self, user_id: uuid.UUID, address_id: uuid.UUID
    ) -> bool:
        """Atomically pivot the default flag to a single row.

        A single UPDATE statement clears every other default and sets
        the target — there is never a moment where the table holds two
        defaults for the same user. The partial unique index added in
        m_006 enforces this at the DB level, so this query also serves
        as a guard against parallel writers racing.

        Returns True iff the target address exists, belongs to the user,
        and is not soft-deleted (rowcount=1). False if the address is
        missing, owned by someone else, or deleted (rowcount=0) —
        caller should 404.
        """
        # First confirm the target exists for this user and is not deleted.
        # We need this because the bulk UPDATE below would silently no-op
        # otherwise, and we can't distinguish that from "target already
        # is_default" by rowcount alone.
        target = await self.get_by_id(user_id, address_id)
        if target is None:
            return False

        stmt = (
            update(UserAddress)
            .where(
                UserAddress.user_id == user_id,
                UserAddress.is_deleted.is_(False),
            )
            .values(
                is_default=case(
                    (UserAddress.id == address_id, True),
                    else_=False,
                )
            )
        )
        await self._db.execute(stmt)
        return True

    async def clear_default(self, user_id: uuid.UUID) -> None:
        """Used by the service when deleting the current default — flips
        is_default to False on every active row so we don't violate the
        partial unique on a subsequent create."""
        stmt = (
            update(UserAddress)
            .where(
                UserAddress.user_id == user_id,
                UserAddress.is_default.is_(True),
                UserAddress.is_deleted.is_(False),
            )
            .values(is_default=False)
        )
        await self._db.execute(stmt)

    async def first_active(
        self, user_id: uuid.UUID, exclude_id: uuid.UUID | None = None
    ) -> UserAddress | None:
        """First-by-created_at active address, optionally excluding one
        (used after deleting the current default to pick a new default)."""
        conds = [
            UserAddress.user_id == user_id,
            UserAddress.is_deleted.is_(False),
        ]
        if exclude_id is not None:
            conds.append(UserAddress.id != exclude_id)
        stmt = (
            select(UserAddress)
            .where(and_(*conds))
            .order_by(UserAddress.created_at.asc())
            .limit(1)
        )
        return await self._db.scalar(stmt)
