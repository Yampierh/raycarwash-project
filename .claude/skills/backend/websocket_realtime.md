---
name: backend-websocket-realtime
description: WebSocket connection and room management patterns. Use when implementing real-time features (GPS tracking, status updates, notifications). Covers connection manager, JWT auth, and Redis pub/sub.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - failure_modes
  - async_workers
preconditions:
  - JWT token verified on every connection
  - Redis pub/sub for multi-instance support
  - ConnectionManager in app.state.ws_manager
outputs:
  - WebSocket room per appointment
  - Real-time status/location/ETA push
conflicts:
  - WS event sent AFTER DB commit (never before)
  - No auth bypass on WebSocket connect
execution_priority: 2
---

# WebSocket Real-Time

**Priority: HIGH**  
**Applies to:** Real-time status updates, GPS tracking, notification broadcasts

## Architecture

```
Client WS ──→ /ws/appointments/{id}?token=<jwt>
            │
            ▼
ConnectionManager (app.state.ws_manager)
            │
    ┌───────┼────────┐
    ▼       ▼        ▼
 Room 1  Room 2   Room 3
 (appt)  (appt)   (appt)
```

## Connection Manager

```python
# app/ws/connection_manager.py
from fastapi import WebSocket
import json
from typing import Any


class ConnectionManager:
    def __init__(self, redis: Redis):
        self._redis = redis
        self._rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        await websocket.accept()
        if room_id not in self._rooms:
            self._rooms[room_id] = set()
        self._rooms[room_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        if room_id in self._rooms:
            self._rooms[room_id].discard(websocket)
            if not self._rooms[room_id]:
                del self._rooms[room_id]

    async def send_to_room(self, room_id: str, message: dict[str, Any]) -> None:
        if room_id not in self._rooms:
            return
        dead = []
        for ws in self._rooms[room_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._rooms[room_id].discard(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for room_id in self._rooms:
            await self.send_to_room(room_id, message)

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        await self._redis.publish(channel, json.dumps(message))
```

## Router with JWT Auth

```python
# app/ws/router.py
from fastapi import WebSocket, WebSocketDisconnect, Query
from app.core.auth import decode_token
from app.ws.connection_manager import ConnectionManager


@router.websocket("/ws/appointments/{appointment_id}")
async def appointment_ws(
    websocket: WebSocket,
    appointment_id: str,
    token: str = Query(...),
):
    # 1. JWT auth from query param
    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # 2. Verify user has access to this appointment
    # (client who booked or detailer assigned)
    ws_manager: ConnectionManager = websocket.app.state.ws_manager

    await ws_manager.connect(websocket, f"appt:{appointment_id}")

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            await ws_manager.send_to_room(
                f"appt:{appointment_id}",
                {"type": "echo", "data": data},
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, f"appt:{appointment_id}")
```

## Event Types

Standard message format sent to clients:

```python
# Status update events
await ws_manager.send_to_room(
    f"appt:{appointment_id}",
    {
        "type": "status_update",
        "data": {
            "status": new_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    },
)

# GPS location update
await ws_manager.send_to_room(
    f"appt:{appointment_id}",
    {
        "type": "location_update",
        "data": {
            "lat": detailer.lat,
            "lng": detailer.lng,
            "heading": detailer.heading,
            "speed": detailer.speed,
            "timestamp": detailer.updated_at.isoformat(),
        },
    },
)

# ETA update
await ws_manager.send_to_room(
    f"appt:{appointment_id}",
    {
        "type": "eta_update",
        "data": {
            "eta_minutes": eta,
            "distance_miles": distance,
        },
    },
)
```

## Redis Pub/Sub (Cross-Instance)

For multi-instance deployments, workers publish to Redis channels:

```python
# Worker publishes
await redis.publish(
    f"appt:{appointment_id}",
    json.dumps({"type": "location_update", "data": {...}}),
)

# WS router subscribes via Redis
async def appointment_ws(...):
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"appt:{appointment_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_json(json.loads(message["data"]))
    finally:
        await pubsub.unsubscribe(f"appt:{appointment_id}")
```

## Anti-Patterns

```python
# ❌ BAD: Storing active WebSocket in memory (not distributed)
self._active_connections: list[WebSocket] = []
# Fails on multiple API instances

# ✅ GOOD: Redis pub/sub for multi-instance
await redis.publish(channel, json.dumps(message))

# ❌ BAD: No auth on WebSocket
@router.websocket("/ws/{room_id}")
async def ws(room_id: str, websocket: WebSocket):
    await websocket.accept()
    # Anyone can connect

# ✅ GOOD: JWT auth on connect
try:
    payload = decode_token(token)
except Exception:
    await websocket.close(code=4001)

# ❌ BAD: No reconnection handling in client code
# Connection drops silently

# ✅ GOOD: Client reconnect logic (frontend responsibility)
# The WS hook should implement exponential backoff reconnection
```

## Success Criteria

- JWT token verified on every WebSocket connection
- Room-based messaging (per appointment)
- Redis pub/sub for multi-instance support
- Graceful disconnect handling
- Workers can publish to Redis channel
- Client hook handles reconnection