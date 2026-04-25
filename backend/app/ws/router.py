# app/ws/router.py
#
# WebSocket endpoint for real-time appointment updates.
#
# Endpoint: WS /ws/appointments/{appointment_id}?token=<jwt>
#
# Message protocol (JSON):
#
#   Client/Detailer → Server:
#     { "type": "ping" }
#     { "type": "location_update", "lat": float, "lng": float }  (detailer only)
#
#   Server → Client/Detailer:
#     { "type": "pong" }
#     { "type": "status_change",   "status": str, "appointment_id": str, "ts": str }
#     { "type": "location_update", "lat": float, "lng": float, "ts": str }
#
# Access control:
#   - JWT must be a valid access token (passed as ?token= query param)
#   - Caller must be the client, the detailer, or an admin of the appointment
#
# HOW TO TEST MANUALLY:
#   npx wscat -c "ws://localhost:8000/ws/appointments/{id}?token={jwt}"

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_db
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.provider_repository import ProviderRepository
from app.services.auth import ws_get_current_user
from app.ws.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


# ------------------------------------------------------------------ #
#  Dependency: singleton ConnectionManager from app.state            #
# ------------------------------------------------------------------ #

def get_ws_manager(request: Request) -> ConnectionManager:
    return request.app.state.ws_manager


# ------------------------------------------------------------------ #
#  WebSocket endpoint                                                 #
# ------------------------------------------------------------------ #

@router.websocket("/ws/appointments/{appointment_id}")
async def appointment_ws(
    websocket: WebSocket,
    appointment_id: uuid.UUID,
    token: str = Query(..., description="Valid JWT access token"),
    db: AsyncSession = Depends(get_db),
    manager: ConnectionManager = Depends(get_ws_manager),
) -> None:
    """
    Room-based WebSocket for a single appointment.

    Both the client and the detailer connect here using the appointment ID.
    All status change broadcasts from HTTP endpoints arrive here too.
    """
    # ---- Auth -------------------------------------------------------- #
    current_user = await ws_get_current_user(token, db)
    if current_user is None:
        await websocket.close(code=4001)  # Unauthorized
        return

    # ---- Access gate ------------------------------------------------- #
    appt_repo = AppointmentRepository(db)
    appt = await appt_repo.get_by_id(appointment_id)
    if appt is None:
        await websocket.close(code=4004)  # Not found
        return

    is_participant = current_user.id in (appt.client_id, appt.detailer_id)
    if not is_participant and not current_user.is_admin():
        await websocket.close(code=4003)  # Forbidden
        return

    is_detailer = current_user.is_detailer()

    # ---- Join room --------------------------------------------------- #
    await manager.connect(appointment_id, websocket)

    # Forward Redis Pub/Sub messages to this WebSocket concurrently
    forward_task = asyncio.create_task(
        manager.subscribe_and_forward(websocket, appointment_id)
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "location_update" and is_detailer:
                lat = data.get("lat")
                lng = data.get("lng")
                if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                    continue

                # Persist to DB in the background using a dedicated session —
                # the WS session must NOT be shared with concurrent tasks.
                asyncio.create_task(
                    _persist_location(current_user.id, float(lat), float(lng))
                )

                # Broadcast to the room via Redis Pub/Sub
                await manager.broadcast(
                    appointment_id,
                    {
                        "type": "location_update",
                        "lat": lat,
                        "lng": lng,
                        "ts": datetime.now(timezone.utc).isoformat(),
                    },
                )

    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass
        await manager.disconnect(appointment_id, websocket)


# ------------------------------------------------------------------ #
#  Personal WebSocket endpoint (detailer offers / push notifications) #
# ------------------------------------------------------------------ #

@router.websocket("/ws/user/{user_id}")
async def user_ws(
    websocket: WebSocket,
    user_id: uuid.UUID,
    token: str = Query(..., description="Valid JWT access token"),
    manager: ConnectionManager = Depends(get_ws_manager),
) -> None:
    """
    Personal channel for a single user. Used by the DetailerHomeScreen
    to receive offer notifications from the assignment engine.
    Room key: user:{user_id}
    """
    async with AsyncSessionLocal() as db:
        current_user = await ws_get_current_user(token, db)

    if current_user is None:
        await websocket.close(code=4001)
        return
    if current_user.id != user_id:
        await websocket.close(code=4003)
        return

    room_id = f"user:{user_id}"
    await manager.connect(room_id, websocket)
    forward_task = asyncio.create_task(manager.subscribe_and_forward(websocket, room_id))

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass
        await manager.disconnect(room_id, websocket)


# ------------------------------------------------------------------ #
#  Background helpers                                                 #
# ------------------------------------------------------------------ #

async def _persist_location(
    user_id: uuid.UUID,
    lat: float,
    lng: float,
) -> None:
    """
    Fire-and-forget: write location to DB without blocking the WS receive loop.

    Opens its own session so it never contends with the WebSocket session.
    SQLAlchemy async sessions are NOT safe for concurrent access from multiple
    coroutines, so sharing the WS session here would cause intermittent errors.
    """
    try:
        async with AsyncSessionLocal() as db:
            repo = ProviderRepository(db)
            await repo.update_location(user_id, lat, lng)
            await db.commit()
    except Exception as exc:
        logger.warning("Failed to persist WS location | user=%s err=%s", user_id, exc)
