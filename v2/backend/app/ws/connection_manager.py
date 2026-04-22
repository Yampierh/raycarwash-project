from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

logger = logging.getLogger(__name__)

_ROOM_CHANNEL = "ws:room:{room_id}"


class ConnectionManager:
    """
    Redis Pub/Sub-backed WebSocket room manager.

    Unlike v1's in-memory dict, this implementation routes all broadcasts
    through Redis so multiple uvicorn workers can serve the same room.

    Architecture:
      - broadcast()  → redis.publish(channel, payload)
      - Each WS connection subscribes to its room channel and forwards
        messages to the connected socket in subscribe_and_forward().

    Scaling: works across any number of uvicorn workers as long as they
    share the same Redis instance. For geographic distribution, use
    Redis Cluster with consistent hashing on appointment_id.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    # ---------------------------------------------------------------- #
    #  Publish (server → room)                                         #
    # ---------------------------------------------------------------- #

    async def broadcast(self, room_id: str | uuid.UUID, payload: dict[str, Any]) -> None:
        channel = _ROOM_CHANNEL.format(room_id=str(room_id))
        try:
            await self._redis.publish(channel, json.dumps(payload))
        except Exception as exc:
            logger.error("WS broadcast failed | room=%s err=%s", room_id, exc)

    # ---------------------------------------------------------------- #
    #  Subscribe (forwards channel messages to a single WebSocket)     #
    # ---------------------------------------------------------------- #

    async def subscribe_and_forward(
        self,
        websocket: WebSocket,
        room_id: str | uuid.UUID,
    ) -> None:
        """
        Subscribe to the room's Redis channel and relay every published
        message to `websocket` until the connection is closed.

        Called as an asyncio.Task so the WS receive loop can run concurrently.
        """
        channel = _ROOM_CHANNEL.format(room_id=str(room_id))
        async with self._redis.pubsub() as ps:
            await ps.subscribe(channel)
            try:
                async for message in ps.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        await websocket.send_text(message["data"])
                    except Exception:
                        # Socket closed — stop forwarding
                        break
            finally:
                await ps.unsubscribe(channel)
