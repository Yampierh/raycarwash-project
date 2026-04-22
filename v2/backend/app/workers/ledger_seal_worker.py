from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from app.db.session import AsyncSessionLocal
from app.repositories.ledger_repository import LedgerRepository

logger = logging.getLogger(__name__)

# System service account UUID — must exist in the users table.
# Create a dedicated "system" user at seed time and use its ID here.
SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def seal_previous_day() -> None:
    """
    Seal all ledger entries for the previous UTC calendar day.

    Idempotent: if a seal for yesterday already exists, this is a no-op.
    Runs nightly via the asyncio task started in main.py lifespan.
    """
    yesterday = date.today() - timedelta(days=1)
    start = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=timezone.utc)
    end   = start + timedelta(days=1)

    async with AsyncSessionLocal() as db:
        repo = LedgerRepository(db)

        existing = await repo.get_seal(yesterday)
        if existing:
            logger.info("Ledger already sealed for %s — skipping.", yesterday)
            return

        entries = await repo.get_by_date_range(start, end)
        if not entries:
            logger.info("No ledger entries for %s — skipping seal.", yesterday)
            return

        seal = await repo.create_seal(yesterday, entries, SYSTEM_USER_ID)
        await db.commit()

    logger.info(
        "Ledger sealed | date=%s entries=%d total_cents=%d checksum=%s",
        seal.sealed_date,
        seal.entry_count,
        seal.total_amount_cents,
        seal.checksum[:16] + "...",
    )


async def run() -> None:
    """
    Nightly seal loop.

    Fires once per day at 00:05 UTC (5 minutes after midnight to allow
    any in-flight transactions from the last minute of the day to settle).
    """
    logger.info("Ledger Seal Worker started.")
    while True:
        try:
            now = datetime.now(timezone.utc)
            # Next run at 00:05 UTC tomorrow
            next_run = datetime(
                now.year, now.month, now.day,
                0, 5, 0, tzinfo=timezone.utc,
            ) + timedelta(days=1)
            sleep_seconds = (next_run - now).total_seconds()
            logger.info("Ledger Seal Worker sleeping %.0f seconds until %s", sleep_seconds, next_run)
            await asyncio.sleep(sleep_seconds)
            await seal_previous_day()
        except asyncio.CancelledError:
            logger.info("Ledger Seal Worker shutting down.")
            break
        except Exception as exc:
            logger.error("Ledger Seal Worker error: %s", exc)
            await asyncio.sleep(60)
