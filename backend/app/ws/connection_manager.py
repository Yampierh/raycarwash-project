# app/ws/connection_manager.py
#
# In-memory asyncio WebSocket connection manager.
#
# Rooms are keyed by appointment_id (str).  Both the client and the detailer
# for an appointment join the same room so they receive each other's events.
#
# Scale path: the dict + asyncio.Lock is correct for a single uvicorn worker.
# When you need multi-worker scale, replace _rooms with a Redis pub/sub channel
# per appointment_id — the public method signatures stay the same.

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    # ---------------------------------------------------------------- #
    #  Connection lifecycle                                             #
    # ---------------------------------------------------------------- #

    async def connect(self, appointment_id: uuid.UUID, ws: WebSocket) -> None:
        await ws.accept()
        key = str(appointment_id)
        async with self._lock:
            self._rooms.setdefault(key, set()).add(ws)
        logger.info(
            "WS connected | room=%s size=%d", key, len(self._rooms[key])
        )

    async def disconnect(self, appointment_id: uuid.UUID, ws: WebSocket) -> None:
        key = str(appointment_id)
        async with self._lock:
            room = self._rooms.get(key, set())
            room.discard(ws)
            if not room:
                self._rooms.pop(key, None)
        logger.info("WS disconnected | room=%s", key)

    # ---------------------------------------------------------------- #
    #  Broadcast                                                        #
    # ---------------------------------------------------------------- #

    async def broadcast(
        self,
        appointment_id: uuid.UUID,
        message: dict[str, Any],
        exclude: WebSocket | None = None,
    ) -> None:
        """Send JSON to every socket in the room, silently purging dead ones."""
        key = str(appointment_id)
        async with self._lock:
            members = set(self._rooms.get(key, set()))

        dead: list[WebSocket] = []
        for ws in members:
            if ws is exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("WS send failed — marking dead | room=%s", key)
                dead.append(ws)

        if dead:
            async with self._lock:
                room = self._rooms.get(key, set())
                for ws in dead:
                    room.discard(ws)

    # ---------------------------------------------------------------- #
    #  Utility                                                          #
    # ---------------------------------------------------------------- #

    def room_size(self, appointment_id: uuid.UUID) -> int:
        return len(self._rooms.get(str(appointment_id), set()))
