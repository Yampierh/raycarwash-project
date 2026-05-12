"""
Push notification service — Expo Push API.

Sends notifications via Expo's push gateway which internally handles
FCM (Android) and APNs (iOS) delivery. No Firebase project required for
Expo managed workflow; tokens have the format ExponentPushToken[...].
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_EXPO_PUSH_URL = "https://exp.host/--/exponent-push-token/v2/push"
_CHUNK_SIZE = 100  # Expo max per request


class PushNotificationService:

    @staticmethod
    async def send(
        tokens: list[str],
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        badge: int | None = None,
        sound: str = "default",
    ) -> None:
        """Send a push notification to a list of Expo push tokens.

        Silently logs failures — a push failure must never break the main flow.
        """
        if not tokens:
            return

        # Build message list; filter out empty tokens
        messages = [
            {
                "to": token,
                "title": title,
                "body": body,
                "sound": sound,
                **({"data": data} if data else {}),
                **({"badge": badge} if badge is not None else {}),
            }
            for token in tokens
            if token
        ]

        if not messages:
            return

        # Send in chunks of 100 (Expo limit)
        async with httpx.AsyncClient(timeout=10.0) as client:
            for i in range(0, len(messages), _CHUNK_SIZE):
                chunk = messages[i : i + _CHUNK_SIZE]
                try:
                    response = await client.post(
                        _EXPO_PUSH_URL,
                        json=chunk,
                        headers={"Accept": "application/json", "Content-Type": "application/json"},
                    )
                    response.raise_for_status()
                    result = response.json()
                    # Log per-ticket errors from Expo without raising
                    for j, ticket in enumerate(result.get("data", [])):
                        if ticket.get("status") == "error":
                            logger.warning(
                                "Push delivery error | token=%s details=%s",
                                chunk[j].get("to", "?"),
                                ticket.get("details"),
                            )
                except Exception:
                    logger.exception(
                        "Failed to send push notifications to %d tokens (chunk %d)",
                        len(chunk), i // _CHUNK_SIZE,
                    )
