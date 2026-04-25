# app/repositories/appointment_repository.py  —  Sprint 3
#
# CRITICAL ADDITION: SELECT FOR UPDATE via PostgreSQL advisory locks.
#
# WHY advisory locks instead of row-level FOR UPDATE?
# The naive FOR UPDATE approach would be:
#     SELECT * FROM appointments
#     WHERE detailer_id = $1 AND ... overlap condition ...
#     FOR UPDATE
# This fails because if there are NO existing appointments (empty result),
# there are no rows to lock — the INSERT races through unprotected.
#
# PostgreSQL advisory locks solve this cleanly:
#   pg_advisory_xact_lock(bigint) acquires an exclusive session-level
#   lock scoped to the current transaction. Any second transaction trying
#   to acquire the same lock BLOCKS until the first commits or rolls back.
#   The lock key is derived from the detailer's UUID — so only concurrent
#   bookings for the SAME detailer contend; bookings for different
#   detailers never block each other.
#
# The full atomic sequence is:
#   1. BEGIN (managed by get_db's context manager)
#   2. SELECT pg_advisory_xact_lock(detailer_lock_key)  ← blocks here if contested
#   3. Re-run overlap check within locked transaction
#   4. INSERT if clean
#   5. COMMIT (managed by get_db) → lock auto-released
#
# This guarantees serializable behaviour for the booking flow without
# needing SERIALIZABLE isolation on the entire DB connection.

from __future__ import annotations

import struct
import uuid
from datetime import datetime

from sqlalchemy import and_, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.models.models import Appointment, AppointmentStatus, TERMINAL_STATUSES


def _detailer_lock_key(detailer_id: uuid.UUID) -> int:
    """
    Derive a stable 64-bit integer key from a UUID for pg_advisory_xact_lock.

    Takes the first 8 bytes of the UUID and unpacks as a signed 64-bit
    big-endian integer — guaranteed to be within PostgreSQL's bigint range.
    The same UUID always produces the same key, and different UUIDs almost
    always produce different keys (collision probability ≈ 1/2^64).
    """
    return struct.unpack(">q", detailer_id.bytes[:8])[0]


class AppointmentRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ---------------------------------------------------------------- #
    #  Concurrency-safe create                                          #
    # ---------------------------------------------------------------- #

    async def acquire_detailer_lock(self, detailer_id: uuid.UUID) -> None:
        """
        Acquire an exclusive transaction-scoped advisory lock for the
        given detailer.

        This MUST be called inside an active transaction before running
        get_overlapping_count() + create(). The lock is released
        automatically when the transaction commits or rolls back.

        Blocks (does not time out by default) if another transaction holds
        the same key. For a marketplace, this is acceptable — the wait is
        bounded by one DB round-trip (the overlapping INSERT transaction).
        To add a timeout, set: SET lock_timeout = '3s'; before acquiring.
        """
        lock_key = _detailer_lock_key(detailer_id)
        await self._db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": lock_key},
        )

    async def get_overlapping_count(
        self,
        detailer_id: uuid.UUID,
        new_start: datetime,
        new_buffer_end: datetime,
    ) -> int:
        """
        Count active appointments that overlap with [new_start, new_buffer_end).

        MUST be called after acquire_detailer_lock() to be race-condition safe.

        Interval overlap formula:  A < D  AND  C < B
        Where this appointment = [new_start, new_buffer_end)
        And existing           = [scheduled_time, travel_buffer_end_time)
        """
        stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(
                and_(
                    Appointment.detailer_id == detailer_id,
                    Appointment.is_deleted.is_(False),
                    not_(Appointment.status.in_(list(TERMINAL_STATUSES))),
                    Appointment.scheduled_time < new_buffer_end,
                    Appointment.travel_buffer_end_time > new_start,
                )
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def create(self, appointment: Appointment) -> Appointment:
        """
        Persist a new Appointment.

        This method intentionally does NOT acquire the advisory lock itself —
        callers must call acquire_detailer_lock() first. This design keeps
        the lock acquisition explicit in the service layer, where the full
        check-then-insert sequence is visible in one place.
        """
        self._db.add(appointment)
        await self._db.flush()
        await self._db.refresh(appointment)
        return appointment

    # ---------------------------------------------------------------- #
    #  Read queries                                                      #
    # ---------------------------------------------------------------- #

    async def get_by_id(self, appointment_id: uuid.UUID) -> Appointment | None:
        stmt = select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_detailer_on_date(
        self,
        detailer_id: uuid.UUID,
        day_start: datetime,
        day_end: datetime,
    ) -> list[Appointment]:
        """
        Fetch all non-terminal appointments for a detailer on a given calendar day.

        Used by the availability engine to determine occupied slots.
        Returns appointments ordered by scheduled_time for sequential
        slot generation.
        """
        stmt = (
            select(Appointment)
            .where(
                and_(
                    Appointment.detailer_id == detailer_id,
                    Appointment.is_deleted.is_(False),
                    not_(Appointment.status.in_(list(TERMINAL_STATUSES))),
                    Appointment.scheduled_time >= day_start,
                    Appointment.scheduled_time < day_end,
                )
            )
            .order_by(Appointment.scheduled_time.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_for_detailer(
        self,
        detailer_id: uuid.UUID,
    ) -> Appointment | None:
        """
        Return the single appointment currently in ARRIVED or IN_PROGRESS state
        for this detailer.  Used by the WebSocket layer to find which room to
        broadcast location updates to.  Returns None if no active job exists.
        """
        stmt = (
            select(Appointment)
            .where(
                and_(
                    Appointment.detailer_id == detailer_id,
                    Appointment.is_deleted.is_(False),
                    Appointment.status.in_([
                        AppointmentStatus.ARRIVED,
                        AppointmentStatus.IN_PROGRESS,
                    ]),
                )
            )
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_client(
        self,
        client_id: uuid.UUID,
        status: AppointmentStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Appointment], int]:
        """Return paginated appointments for a client + total count."""
        conditions = [
            Appointment.client_id == client_id,
            Appointment.is_deleted.is_(False),
        ]
        if status is not None:
            conditions.append(Appointment.status == status)

        count_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(and_(*conditions))
        )
        total: int = (await self._db.execute(count_stmt)).scalar_one()

        stmt = (
            select(Appointment)
            .where(and_(*conditions))
            .order_by(Appointment.scheduled_time.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_detailer(
        self,
        detailer_id: uuid.UUID,
        status: AppointmentStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Appointment], int]:
        """Return paginated appointments for a detailer + total count."""
        conditions = [
            Appointment.detailer_id == detailer_id,
            Appointment.is_deleted.is_(False),
        ]
        if status is not None:
            conditions.append(Appointment.status == status)

        count_stmt = (
            select(func.count())
            .select_from(Appointment)
            .where(and_(*conditions))
        )
        total: int = (await self._db.execute(count_stmt)).scalar_one()

        stmt = (
            select(Appointment)
            .where(and_(*conditions))
            .order_by(Appointment.scheduled_time.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total