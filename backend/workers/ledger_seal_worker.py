from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import date, datetime, timedelta, timezone

from infrastructure.db.session import AsyncSessionLocal
from domains.payments.models import LedgerSeal
from domains.payments.repository import LedgerRepository

logger = logging.getLogger(__name__)


async def _seal_day(target_date: date) -> None:
    async with AsyncSessionLocal() as db:
        repo = LedgerRepository(db)

        if await repo.seal_exists(target_date):
            logger.info("Ledger already sealed for %s — skipping", target_date)
            return

        entries = await repo.get_entries_for_date(target_date)
        if not entries:
            logger.info("No ledger entries for %s — skipping seal", target_date)
            return

        entry_count = len(entries)
        total_cents = sum(e.amount_cents for e in entries)

        sorted_ids = sorted(str(e.id) for e in entries)
        sha256 = hashlib.sha256("".join(sorted_ids).encode()).hexdigest()

        seal = LedgerSeal(
            seal_date=target_date,
            entry_count=entry_count,
            total_amount_cents=total_cents,
            sha256_hash=sha256,
        )
        await repo.create_seal(seal)
        await db.commit()
        logger.info(
            "Ledger sealed | date=%s entries=%d total=%d¢ sha256=%s...",
            target_date, entry_count, total_cents, sha256[:12],
        )


async def ledger_seal_worker(_app_state) -> None:
    logger.info("Ledger seal worker started")
    while True:
        try:
            now = datetime.now(timezone.utc)
            next_midnight = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            sleep_seconds = (next_midnight - now).total_seconds()
            logger.info("Ledger seal worker sleeping %.0fs until %s UTC", sleep_seconds, next_midnight.date())
            await asyncio.sleep(sleep_seconds)

            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
            await _seal_day(yesterday)

        except asyncio.CancelledError:
            logger.info("Ledger seal worker stopped")
            return
        except Exception as exc:
            logger.error("ledger_seal_worker error: %s", exc)
            await asyncio.sleep(60)
