from __future__ import annotations

import asyncio
import logging
import uuid

import redis.asyncio as aioredis

from app.services.assignment_service import assign_appointment

logger = logging.getLogger(__name__)

STREAM_NAME    = "assignment_queue"
CONSUMER_GROUP = "assignment_worker_group"
CONSUMER_NAME  = "worker-1"


async def run(redis_client: aioredis.Redis) -> None:
    """
    Redis Streams consumer for the assignment queue.

    Each message triggers the full detailer assignment algorithm:
      H3 k-ring search → scoring → Redis lock → offer → accept/timeout
    """
    try:
        await redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info("Assignment Worker consumer group created.")
    except Exception:
        pass  # Group already exists

    logger.info("Assignment Worker started — consuming stream '%s'", STREAM_NAME)

    while True:
        try:
            results = await redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_NAME: ">"},
                count=5,
                block=2000,
            )

            if not results:
                continue

            for _stream, messages in results:
                for message_id, fields in messages:
                    asyncio.create_task(
                        _handle_message(redis_client, message_id, fields)
                    )

        except asyncio.CancelledError:
            logger.info("Assignment Worker shutting down.")
            break
        except Exception as exc:
            logger.error("Assignment Worker loop error: %s", exc)
            await asyncio.sleep(1)


async def _handle_message(
    redis_client: aioredis.Redis,
    message_id: str,
    fields: dict[str, str],
) -> None:
    appointment_id = fields["appointment_id"]
    client_lat     = float(fields["client_lat"])
    client_lng     = float(fields["client_lng"])
    service_id     = fields["service_id"]

    try:
        assigned = await assign_appointment(
            redis_client,
            appointment_id,
            client_lat,
            client_lng,
            service_id,
        )

        if not assigned:
            await _mark_no_detailer_found(appointment_id)

        await redis_client.xack(STREAM_NAME, CONSUMER_GROUP, message_id)

    except Exception as exc:
        logger.error(
            "Assignment Worker message error | id=%s appointment=%s err=%s",
            message_id, appointment_id, exc,
        )


async def _mark_no_detailer_found(appointment_id: str) -> None:
    from app.db.session import AsyncSessionLocal
    from app.repositories.appointment_repository import AppointmentRepository
    from app.models.models import AppointmentStatus

    async with AsyncSessionLocal() as db:
        repo = AppointmentRepository(db)
        appt = await repo.get_by_id(uuid.UUID(appointment_id))
        if appt:
            appt.status = AppointmentStatus.NO_DETAILER_FOUND
            await db.commit()
    logger.warning("No detailer found for appointment=%s", appointment_id)
