from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from domains.payments.models import PaymentLedger
from domains.payments.repository import LedgerRepository

logger = logging.getLogger(__name__)

COMMISSION_RATE = 0.15  # 15% platform commission


# ------------------------------------------------------------------ #
#  Abstract processor interface                                        #
# ------------------------------------------------------------------ #

class PaymentProcessor(ABC):
    @abstractmethod
    async def authorize(self, appointment_id: str, amount_cents: int, currency: str = "usd") -> dict:
        ...

    @abstractmethod
    async def capture(self, authorization_id: str, amount_cents: int) -> dict:
        ...

    @abstractmethod
    async def refund(self, authorization_id: str, amount_cents: int) -> dict:
        ...

    @abstractmethod
    async def payout(self, detailer_id: str, amount_cents: int) -> dict:
        ...


# ------------------------------------------------------------------ #
#  Mock processor — safe for dev, logs every operation               #
# ------------------------------------------------------------------ #

class MockPaymentProcessor(PaymentProcessor):
    async def authorize(self, appointment_id: str, amount_cents: int, currency: str = "usd") -> dict:
        result = {"id": f"pi_mock_{uuid.uuid4().hex[:12]}", "status": "authorized", "amount": amount_cents}
        logger.info("MOCK authorize | appt=%s amount=%d%s result=%s", appointment_id, amount_cents, currency, result["id"])
        return result

    async def capture(self, authorization_id: str, amount_cents: int) -> dict:
        result = {"id": f"ch_mock_{uuid.uuid4().hex[:12]}", "status": "captured", "amount": amount_cents}
        logger.info("MOCK capture | auth=%s amount=%d result=%s", authorization_id, amount_cents, result["id"])
        return result

    async def refund(self, authorization_id: str, amount_cents: int) -> dict:
        result = {"id": f"re_mock_{uuid.uuid4().hex[:12]}", "status": "refunded", "amount": amount_cents}
        logger.info("MOCK refund | auth=%s amount=%d result=%s", authorization_id, amount_cents, result["id"])
        return result

    async def payout(self, detailer_id: str, amount_cents: int) -> dict:
        result = {"id": f"po_mock_{uuid.uuid4().hex[:12]}", "status": "paid_out", "amount": amount_cents}
        logger.info("MOCK payout | detailer=%s amount=%d result=%s", detailer_id, amount_cents, result["id"])
        return result


# ------------------------------------------------------------------ #
#  Coordinator: processor + ledger                                    #
# ------------------------------------------------------------------ #

class PaymentCoordinator:
    def __init__(self, db: AsyncSession, processor: PaymentProcessor | None = None) -> None:
        self._db = db
        self._processor = processor or MockPaymentProcessor()
        self._ledger = LedgerRepository(db)

    async def authorize(self, appointment_id: uuid.UUID, amount_cents: int, currency: str = "usd") -> PaymentLedger:
        result = await self._processor.authorize(str(appointment_id), amount_cents, currency)
        entry = PaymentLedger(
            appointment_id=appointment_id,
            entry_type="AUTHORIZATION",
            amount_cents=amount_cents,
            currency=currency,
            stripe_payment_intent_id=result.get("id"),
            metadata_=result,
        )
        await self._ledger.create(entry)
        await self._db.commit()
        return entry

    async def capture(self, appointment_id: uuid.UUID, amount_cents: int) -> PaymentLedger:
        result = await self._processor.capture(f"pi_mock_{appointment_id}", amount_cents)
        entry = PaymentLedger(
            appointment_id=appointment_id,
            entry_type="CAPTURE",
            amount_cents=amount_cents,
            stripe_payment_intent_id=result.get("id"),
            metadata_=result,
        )
        await self._ledger.create(entry)
        await self._db.commit()
        return entry

    async def payout_and_commission(
        self, appointment_id: uuid.UUID, detailer_id: uuid.UUID, total_amount_cents: int
    ) -> tuple[PaymentLedger, PaymentLedger]:
        commission = int(total_amount_cents * COMMISSION_RATE)
        payout_amount = total_amount_cents - commission

        payout_result = await self._processor.payout(str(detailer_id), payout_amount)
        payout_entry = PaymentLedger(
            appointment_id=appointment_id,
            entry_type="PAYOUT",
            amount_cents=payout_amount,
            metadata_=payout_result,
        )
        commission_entry = PaymentLedger(
            appointment_id=appointment_id,
            entry_type="CHARGE_COMMISSION",
            amount_cents=commission,
            metadata_={"commission_rate": COMMISSION_RATE},
        )
        await self._ledger.create(payout_entry)
        await self._ledger.create(commission_entry)
        await self._db.commit()
        return payout_entry, commission_entry
