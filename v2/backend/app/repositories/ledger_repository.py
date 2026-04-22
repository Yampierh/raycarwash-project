from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger import LedgerEntryType, LedgerRevision, LedgerSeal, PaymentLedger


class LedgerRepository:
    """
    Append-only interface to the payment ledger.

    IMPORTANT: This repository intentionally exposes NO update() or delete()
    methods. The append-only invariant is enforced at the code level here,
    not just by database constraints. Any correction must go through
    create_revision().
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ---------------------------------------------------------------- #
    #  Write (append-only)                                             #
    # ---------------------------------------------------------------- #

    async def create(self, entry: PaymentLedger) -> PaymentLedger:
        """Insert a new ledger entry. This is the ONLY write method."""
        self._db.add(entry)
        await self._db.flush()
        await self._db.refresh(entry)
        return entry

    # ---------------------------------------------------------------- #
    #  Read                                                             #
    # ---------------------------------------------------------------- #

    async def get_by_id(self, entry_id: uuid.UUID) -> PaymentLedger | None:
        result = await self._db.execute(
            select(PaymentLedger).where(PaymentLedger.id == entry_id)
        )
        return result.scalar_one_or_none()

    async def get_by_appointment(self, appointment_id: uuid.UUID) -> list[PaymentLedger]:
        result = await self._db.execute(
            select(PaymentLedger)
            .where(PaymentLedger.appointment_id == appointment_id)
            .order_by(PaymentLedger.created_at)
        )
        return list(result.scalars().all())

    async def get_net_balance(self, appointment_id: uuid.UUID) -> int:
        """
        Net financial position for an appointment.

        SELECT SUM(amount_cents) FROM payment_ledger WHERE appointment_id = X
        """
        result = await self._db.execute(
            select(func.sum(PaymentLedger.amount_cents)).where(
                PaymentLedger.appointment_id == appointment_id
            )
        )
        total = result.scalar_one_or_none()
        return total or 0

    async def get_by_date_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[PaymentLedger]:
        result = await self._db.execute(
            select(PaymentLedger)
            .where(
                PaymentLedger.created_at >= start,
                PaymentLedger.created_at < end,
            )
            .order_by(PaymentLedger.created_at)
        )
        return list(result.scalars().all())

    async def get_by_stripe_payment_intent(
        self, stripe_payment_intent_id: str
    ) -> PaymentLedger | None:
        result = await self._db.execute(
            select(PaymentLedger).where(
                PaymentLedger.stripe_payment_intent_id == stripe_payment_intent_id,
                PaymentLedger.entry_type == LedgerEntryType.AUTHORIZATION,
            )
        )
        return result.scalar_one_or_none()

    # ---------------------------------------------------------------- #
    #  Seal operations                                                  #
    # ---------------------------------------------------------------- #

    async def get_seal(self, sealed_date: date) -> LedgerSeal | None:
        result = await self._db.execute(
            select(LedgerSeal).where(LedgerSeal.sealed_date == sealed_date)
        )
        return result.scalar_one_or_none()

    async def create_seal(
        self,
        sealed_date: date,
        entries: list[PaymentLedger],
        sealed_by: uuid.UUID,
    ) -> LedgerSeal:
        """
        Seal a calendar day's entries.

        Computes a SHA-256 checksum over all entry IDs (sorted) so the
        sealed set can be independently verified later.
        """
        checksum = hashlib.sha256(
            "|".join(sorted(str(e.id) for e in entries)).encode()
        ).hexdigest()

        seal = LedgerSeal(
            sealed_date=sealed_date,
            entry_count=len(entries),
            total_amount_cents=sum(e.amount_cents for e in entries),
            checksum=checksum,
            sealed_by=sealed_by,
        )
        self._db.add(seal)
        await self._db.flush()
        return seal

    # ---------------------------------------------------------------- #
    #  Revision operations                                              #
    # ---------------------------------------------------------------- #

    async def create_revision(
        self,
        sealed_date: date,
        original_entry_id: uuid.UUID,
        correction_entry: PaymentLedger,
        reason: str,
        approved_by: uuid.UUID,
    ) -> LedgerRevision:
        """
        Record a post-seal correction.

        Caller must first create the corrective PaymentLedger entry,
        then pass it here to link it to the original.
        """
        revision = LedgerRevision(
            sealed_date=sealed_date,
            original_entry_id=original_entry_id,
            correction_entry_id=correction_entry.id,
            reason=reason,
            approved_by=approved_by,
        )
        self._db.add(revision)
        await self._db.flush()
        return revision
