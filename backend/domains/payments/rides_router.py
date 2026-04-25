from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.appointments.models import Appointment, AppointmentAssignment, AppointmentStatus, AssignmentStatus
from domains.payments.models import FareEstimate
from domains.auth.service import get_current_user, require_role
from app.services.fare_service import verify_fare_token
from domains.payments.service_v2 import PaymentCoordinator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rides", tags=["Rides"])


# ------------------------------------------------------------------ #
#  POST /rides/request                                                 #
# ------------------------------------------------------------------ #

@router.post(
    "/request",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a ride using a valid fare token.",
)
async def request_ride(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("client")),
):
    fare_token: str = body.get("fare_token", "")
    if not fare_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fare_token required.")

    # Resolve and verify fare estimate
    result = await db.execute(
        select(FareEstimate).where(FareEstimate.fare_token == fare_token)
    )
    fare = result.scalar_one_or_none()
    if fare is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fare estimate not found.")

    if not verify_fare_token(fare_token, str(fare.id), fare.estimated_price_cents, fare.expires_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fare token invalid or expired.")

    # Create Appointment with status SEARCHING (no detailer yet)
    appointment = Appointment(
        client_id=current_user.id,
        detailer_id=None,
        service_id=fare.service_id,
        scheduled_time=datetime.now(timezone.utc),
        status=AppointmentStatus.SEARCHING,
        estimated_price=fare.estimated_price_cents,
        service_latitude=float(fare.client_lat),
        service_longitude=float(fare.client_lng),
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    # INSERT PaymentLedger(AUTHORIZATION)
    coordinator = PaymentCoordinator(db)
    await coordinator.authorize(appointment.id, fare.estimated_price_cents)

    # Enqueue for assignment worker
    redis = request.app.state.redis
    await redis.xadd("assignment_queue", {
        "appointment_id": str(appointment.id),
        "client_lat": str(float(fare.client_lat)),
        "client_lng": str(float(fare.client_lng)),
    })

    logger.info("Ride requested | appt=%s client=%s", appointment.id, current_user.id)

    return {
        "appointment_id": str(appointment.id),
        "status": appointment.status.value,
        "estimated_price_cents": fare.estimated_price_cents,
    }


# ------------------------------------------------------------------ #
#  PUT /rides/{id}/accept                                              #
# ------------------------------------------------------------------ #

@router.put(
    "/{appointment_id}/accept",
    summary="Detailer accepts the offered ride.",
)
async def accept_ride(
    appointment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("detailer")),
):
    appt_result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.status == AppointmentStatus.SEARCHING,
        )
    )
    appointment = appt_result.scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found or not in SEARCHING state.")

    assign_result = await db.execute(
        select(AppointmentAssignment).where(
            AppointmentAssignment.appointment_id == appointment_id,
            AppointmentAssignment.detailer_id == current_user.id,
            AppointmentAssignment.status == AssignmentStatus.OFFERED.value,
        )
    )
    assignment = assign_result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active offer for this detailer.")

    # Update assignment
    await db.execute(
        update(AppointmentAssignment)
        .where(AppointmentAssignment.id == assignment.id)
        .values(status=AssignmentStatus.ACCEPTED.value, responded_at=datetime.now(timezone.utc))
    )

    # Confirm appointment
    await db.execute(
        update(Appointment)
        .where(Appointment.id == appointment_id)
        .values(status=AppointmentStatus.CONFIRMED, detailer_id=current_user.id)
    )
    await db.commit()

    # Signal assignment service
    event_key = f"{appointment_id}:{current_user.id}"
    app_state = request.app.state
    if event_key in app_state.assignment_events:
        app_state.assignment_responses[event_key] = "accepted"
        app_state.assignment_events[event_key].set()

    # Broadcast confirmation to client's WS room
    redis = request.app.state.redis
    await redis.publish(
        f"ws:room:{appointment_id}",
        __import__("json").dumps({
            "type": "status_change",
            "status": AppointmentStatus.CONFIRMED.value,
            "appointment_id": str(appointment_id),
            "detailer_id": str(current_user.id),
            "ts": datetime.now(timezone.utc).isoformat(),
        }),
    )

    # INSERT PaymentLedger(CAPTURE)
    coordinator = PaymentCoordinator(db)
    await coordinator.capture(appointment_id, appointment.estimated_price)

    logger.info("Ride accepted | appt=%s detailer=%s", appointment_id, current_user.id)
    return {"appointment_id": str(appointment_id), "status": AppointmentStatus.CONFIRMED.value}


# ------------------------------------------------------------------ #
#  PUT /rides/{id}/decline                                             #
# ------------------------------------------------------------------ #

@router.put(
    "/{appointment_id}/decline",
    summary="Detailer declines the offered ride.",
)
async def decline_ride(
    appointment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("detailer")),
):
    assign_result = await db.execute(
        select(AppointmentAssignment).where(
            AppointmentAssignment.appointment_id == appointment_id,
            AppointmentAssignment.detailer_id == current_user.id,
            AppointmentAssignment.status == AssignmentStatus.OFFERED.value,
        )
    )
    assignment = assign_result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active offer for this detailer.")

    await db.execute(
        update(AppointmentAssignment)
        .where(AppointmentAssignment.id == assignment.id)
        .values(status=AssignmentStatus.DECLINED.value, responded_at=datetime.now(timezone.utc))
    )
    await db.commit()

    # Signal assignment service to try next candidate
    event_key = f"{appointment_id}:{current_user.id}"
    app_state = request.app.state
    if event_key in app_state.assignment_events:
        app_state.assignment_responses[event_key] = "declined"
        app_state.assignment_events[event_key].set()

    logger.info("Ride declined | appt=%s detailer=%s", appointment_id, current_user.id)
    return {"appointment_id": str(appointment_id), "status": "declined"}
