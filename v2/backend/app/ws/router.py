from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.db.session import AsyncSessionLocal, get_db
from app.repositories.appointment_repository import AppointmentRepository
from app.services.auth import ws_get_current_user
from app.ws.connection_manager import ConnectionManager

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


def get_ws_manager(request: Request) -> ConnectionManager:
    return request.app.state.ws_manager


@router.websocket("/ws/appointments/{appointment_id}")
async def appointment_ws(
    websocket: WebSocket,
    appointment_id: uuid.UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    manager: ConnectionManager = Depends(get_ws_manager),
) -> None:
    """
    Room-based WebSocket for a single appointment.

    Protocol (JSON messages):
      Client → Server:  { "type": "ping" }
                        { "type": "location_update", "lat": float, "lng": float }  # detailer only
      Server → Client:  { "type": "pong" }
                        { "type": "status_change", "status": str, "ts": str }
                        { "type": "location_update", "lat": float, "lng": float, "ts": str }
                        { "type": "assignment_offer", "appointment_id": str, ... }

    Location updates from the detailer are NOT broadcast directly here.
    They are published to the Redis Stream `location_updates` and processed
    by the Location Worker (Fireball filter → H3 update → pub/sub broadcast).
    This decouples frequency control from the WebSocket handler.
    """
    current_user = await ws_get_current_user(token, db)
    if current_user is None:
        await websocket.close(code=4001)
        return

    appt_repo = AppointmentRepository(db)
    appt = await appt_repo.get_by_id(appointment_id)
    if appt is None:
        await websocket.close(code=4004)
        return

    is_participant = current_user.id in (appt.client_id, appt.detailer_id)
    if not is_participant and not current_user.is_admin():
        await websocket.close(code=4003)
        return

    is_detailer = current_user.is_detailer()

    await websocket.accept()

    # Start a background task that subscribes to the room's Redis channel
    # and forwards all published messages to this socket.
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
                # Enqueue to Redis Stream — Location Worker handles Fireball + H3 + broadcast
                asyncio.create_task(
                    _enqueue_location_update(
                        websocket.app.state.redis,
                        str(current_user.id),
                        str(appointment_id),
                        float(lat),
                        float(lng),
                    )
                )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS error | room=%s err=%s", appointment_id, exc)
    finally:
        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass


async def _enqueue_location_update(
    redis_client: aioredis.Redis,
    detailer_id: str,
    appointment_id: str,
    lat: float,
    lng: float,
) -> None:
    try:
        await redis_client.xadd(
            "location_updates",
            {
                "detailer_id":    detailer_id,
                "appointment_id": appointment_id,
                "lat":            str(lat),
                "lng":            str(lng),
                "ts":             datetime.now(timezone.utc).isoformat(),
            },
            maxlen=10_000,
            approximate=True,
        )
    except Exception as exc:
        logger.warning("Failed to enqueue location update | detailer=%s err=%s", detailer_id, exc)
