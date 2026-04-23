from __future__ import annotations

import asyncio
import logging

from app.db.session import AsyncSessionLocal
from app.services.assignment_service import assign

logger = logging.getLogger(__name__)


async def assignment_worker(app_state) -> None:
    redis = app_state.redis
    last_id = "$"

    logger.info("Assignment worker started")
    while True:
        try:
            messages = await redis.xread({"assignment_queue": last_id}, block=1000, count=5)
        except asyncio.CancelledError:
            logger.info("Assignment worker stopped")
            return
        except Exception as exc:
            logger.error("assignment_worker XREAD error: %s", exc)
            await asyncio.sleep(1)
            continue

        if not messages:
            continue

        for _stream, entries in messages:
            for msg_id, data in entries:
                last_id = msg_id
                try:
                    async with AsyncSessionLocal() as db:
                        await assign(
                            appointment_id=data["appointment_id"],
                            client_lat=float(data["client_lat"]),
                            client_lng=float(data["client_lng"]),
                            redis=redis,
                            db=db,
                            app_state=app_state,
                        )
                except Exception as exc:
                    logger.error("assignment_worker error | id=%s err=%s", msg_id, exc)
