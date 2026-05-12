"""
Notification event handlers.

Subscribes to appointment lifecycle events from the in-process event bus and
sends Expo push notifications to affected users.

Registration: call register_handlers() once at app startup (in main.py lifespan).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from events.bus import bus
from domains.notifications.service import PushNotificationService

logger = logging.getLogger(__name__)

# ── Notification copy ────────────────────────────────────────────────────────

_MESSAGES: dict[str, dict[str, str]] = {
    # sent to detailer
    "appointment.created": {
        "title": "New booking request",
        "body":  "You have a new appointment. Check your dashboard.",
    },
    # sent to client
    "confirmed": {
        "title": "Booking confirmed!",
        "body":  "Your appointment is confirmed. We'll see you soon.",
    },
    "arrived": {
        "title": "Your detailer has arrived",
        "body":  "Head outside — they're ready to start!",
    },
    "in_progress": {
        "title": "Service in progress",
        "body":  "Your car is being detailed right now.",
    },
    "completed": {
        "title": "All done! ⭐",
        "body":  "Your car is ready. How was your experience? Leave a review!",
    },
    "cancelled_by_client": {
        "title": "Appointment cancelled",
        "body":  "The client has cancelled the appointment.",
    },
    "cancelled_by_detailer": {
        "title": "Appointment cancelled",
        "body":  "Your detailer had to cancel. We're sorry for the inconvenience.",
    },
    "no_show": {
        "title": "Marked as no-show",
        "body":  "Your appointment was marked as no-show.",
    },
}


async def _get_tokens_for_users(user_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    """Open a short-lived DB session to fetch push tokens."""
    from infrastructure.db.session import AsyncSessionLocal
    from domains.notifications.repository import DeviceTokenRepository

    async with AsyncSessionLocal() as db:
        repo = DeviceTokenRepository(db)
        return await repo.get_tokens_for_users(user_ids)


async def _send_to_user(user_id: uuid.UUID, key: str, data: dict[str, Any]) -> None:
    msg = _MESSAGES.get(key)
    if msg is None:
        return
    tokens_map = await _get_tokens_for_users([user_id])
    tokens = tokens_map.get(user_id, [])
    if tokens:
        await PushNotificationService.send(
            tokens=tokens,
            title=msg["title"],
            body=msg["body"],
            data=data,
        )


def register_handlers() -> None:
    """Register all notification handlers on the event bus. Call once at startup."""

    @bus.on("appointment.created")
    async def on_appointment_created(payload: dict[str, Any]) -> None:
        detailer_id = payload.get("detailer_id")
        if not detailer_id:
            return
        await _send_to_user(
            uuid.UUID(detailer_id),
            "appointment.created",
            {
                "screen": "AppointmentDetail",
                "appointment_id": payload["appointment_id"],
            },
        )

    @bus.on("appointment.status_changed")
    async def on_status_changed(payload: dict[str, Any]) -> None:
        new_status = payload.get("new_status", "")
        client_id  = payload.get("client_id")
        detailer_id = payload.get("detailer_id")
        appt_data   = {
            "screen": "AppointmentDetail",
            "appointment_id": payload["appointment_id"],
        }

        # Notify client on most transitions
        client_statuses = {
            "confirmed", "arrived", "in_progress",
            "completed", "cancelled_by_detailer", "no_show",
        }
        if new_status in client_statuses and client_id:
            await _send_to_user(uuid.UUID(client_id), new_status, appt_data)

        # Notify detailer on client cancellation
        if new_status == "cancelled_by_client" and detailer_id:
            await _send_to_user(uuid.UUID(detailer_id), "cancelled_by_client", appt_data)

    logger.info("Push notification handlers registered.")
