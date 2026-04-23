# app/ws/connection_manager.py
#
# Redis Pub/Sub connection manager for WebSocket rooms.
#
# Each appointment room is backed by a Redis Pub/Sub channel:
#   ws:room:{appointment_id}
#
# This supports multiple uvicorn workers broadcasting to the same room
# because all workers share the same Redis instance.

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

_RoomId = "uuid.UUID | str"  # type alias comment only


class ConnectionManager:
    def __init__(self, redis) -> None:
        self._redis = redis

    # ---------------------------------------------------------------- #
    #  Connection lifecycle                                             #
    # ---------------------------------------------------------------- #

    async def connect(self, room_id: uuid.UUID | str, ws: WebSocket) -> None:
        await ws.accept()
        logger.info("WS connected | room=%s", str(room_id))

    async def disconnect(self, room_id: uuid.UUID | str, ws: WebSocket) -> None:
        logger.info("WS disconnected | room=%s", str(room_id))

    # ---------------------------------------------------------------- #
    #  Broadcast via Redis Pub/Sub                                      #
    # ---------------------------------------------------------------- #

    async def broadcast(
        self,
        room_id: uuid.UUID | str,
        message: dict[str, Any],
    ) -> None:
        channel = f"ws:room:{room_id}"
        await self._redis.publish(channel, json.dumps(message))

    async def subscribe_and_forward(
        self, websocket: WebSocket, room_id: uuid.UUID | str
    ) -> None:
        """Subscribe to the room channel and forward messages to the WebSocket."""
        channel = f"ws:room:{room_id}"
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    await websocket.send_json(payload)
                except Exception:
                    break
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception:
                pass

    # ---------------------------------------------------------------- #
    #  Utility                                                          #
    # ---------------------------------------------------------------- #

    def room_size(self, appointment_id: uuid.UUID | str) -> int:
        # Redis Pub/Sub doesn't track subscriber count per room here;
        # always return 1 so callers guarded by room_size() > 0 still broadcast.
        return 1
