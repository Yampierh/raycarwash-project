from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.payments.models import LedgerSeal, PaymentLedger


class LedgerRepository:
    """
    Append-only access to the payment ledger.
    No update(), no delete() — ever.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, entry: PaymentLedger) -> PaymentLedger:
        self._db.add(entry)
        await self._db.flush()
        return entry

    async def get_by_appointment(self, appointment_id: uuid.UUID) -> list[PaymentLedger]:
        result = await self._db.execute(
            select(PaymentLedger)
            .where(PaymentLedger.appointment_id == appointment_id)
            .order_by(PaymentLedger.created_at)
        )
        return list(result.scalars().all())

    async def get_entries_for_date(self, seal_date: date) -> list[PaymentLedger]:
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import DATE

        result = await self._db.execute(
            select(PaymentLedger)
            .where(
                func.date(PaymentLedger.created_at) == seal_date
            )
            .order_by(PaymentLedger.id)
        )
        return list(result.scalars().all())

    async def seal_exists(self, seal_date: date) -> bool:
        result = await self._db.execute(
            select(LedgerSeal).where(LedgerSeal.seal_date == seal_date)
        )
        return result.scalar_one_or_none() is not None

    async def create_seal(self, seal: LedgerSeal) -> LedgerSeal:
        self._db.add(seal)
        await self._db.flush()
        return seal
