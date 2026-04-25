# app/routers/appointment_router.py  —  Sprint 3 (final)
#
# CHANGES VS UPLOADED VERSION:
#   1. PATCH /{appointment_id}/status — STATE MACHINE endpoint added.
#      The AppointmentService.transition_status() method existed but had
#      no HTTP route registered, making it unreachable from the API.
#   2. All imports moved to module level. Five inline imports were
#      scattered inside handler bodies (anti-pattern: harder to scan,
#      confuses linters, re-executes import machinery on each request call).
#   3. appointment_id: str → uuid.UUID. FastAPI validates and coerces UUID
#      path params natively; the manual try/except block is not needed.
#   4. Removed redundant `from_attributes=True` in model_validate() calls.
#      _BaseSchema already declares from_attributes=True in model_config,
#      so passing it again in every call is noise.

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.users.models import User
from domains.appointments.repository import AppointmentRepository
from domains.appointments.schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatusUpdate,
    AppointmentVehicleRead,
    _ClientSnap,
    _DetailerSnap,
    _VehicleSnap,
)
from shared.schemas import PaginatedResponse
from domains.appointments.service import AppointmentService
from domains.auth.service import get_current_user
from domains.realtime.connection_manager import ConnectionManager


def _get_ws_manager(request: Request) -> ConnectionManager:
    return request.app.state.ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/appointments", tags=["Appointments"])


def _build_appointment_read(appt) -> AppointmentRead:
    """Build a fully-nested AppointmentRead from an ORM Appointment object."""
    # Nested client
    client_snap = None
    if appt.client:
        client_snap = _ClientSnap(
            full_name=appt.client.full_name,
            phone=appt.client.phone_number,
        )

    # Nested detailer
    detailer_snap = None
    if appt.detailer:
        detailer_snap = _DetailerSnap(full_name=appt.detailer.full_name)

    # Nested vehicles with vehicle snapshot
    vehicles = []
    for av in appt.appointment_vehicles:
        v_snap = None
        if av.vehicle:
            v_snap = _VehicleSnap(
                make=av.vehicle.make,
                model=av.vehicle.model,
                body_class=av.vehicle.body_class,
                color=av.vehicle.color,
            )
        vehicles.append(AppointmentVehicleRead(
            id=av.id,
            vehicle_id=av.vehicle_id,
            vehicle_size=av.vehicle_size,
            price_cents=av.price_cents,
            duration_minutes=av.duration_minutes,
            vehicle=v_snap,
        ))

    return AppointmentRead(
        id=appt.id,
        status=appt.status,
        scheduled_time=appt.scheduled_time,
        estimated_end_time=appt.estimated_end_time,
        travel_buffer_end_time=appt.travel_buffer_end_time,
        service_address=appt.service_address,
        client_notes=appt.client_notes,
        detailer_notes=appt.detailer_notes,
        service_latitude=float(appt.service_latitude) if appt.service_latitude else None,
        service_longitude=float(appt.service_longitude) if appt.service_longitude else None,
        estimated_price=appt.estimated_price,
        actual_price=appt.actual_price,
        arrived_at=appt.arrived_at,
        started_at=appt.started_at,
        completed_at=appt.completed_at,
        stripe_payment_intent_id=appt.stripe_payment_intent_id,
        client=client_snap,
        detailer=detailer_snap,
        vehicles=vehicles,
        client_id=appt.client_id,
        detailer_id=appt.detailer_id,
        vehicle_id=appt.vehicle_id,
        service_id=appt.service_id,
        created_at=appt.created_at,
        updated_at=appt.updated_at,
    )


# ── POST /  (create booking) ──────────────────────────────────────── #

@router.post(
    "",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Book a detailing appointment.",
    responses={
        400: {"description": "Business rule violation (self-booking, wrong role)."},
        401: {"description": "Not authenticated."},
        404: {"description": "Detailer, vehicle, or service not found."},
        409: {"description": "Detailer unavailable at the requested time."},
        422: {"description": "Vehicle not owned by client, or invalid datetime."},
    },
)
async def create_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppointmentRead:
    """
    Full booking flow delegated to AppointmentService:
      1. Validate detailer, vehicle ownership, service existence.
      2. Compute estimated_price = ceil(base_price × SIZE_MULTIPLIERS[size]).
         Example: Diamond Detail + GMC Sierra XL → ceil(25000 × 2.0) = $500.00
      3. Acquire advisory lock → overlap check → INSERT (race-condition safe).

    client_id is extracted from the JWT — it cannot be spoofed.
    """
    svc = AppointmentService(db)
    appointment = await svc.create_appointment(payload=payload, client=current_user)
    return _build_appointment_read(appointment)


# ── PATCH /{id}/status  (STATE MACHINE) ──────────────────────────── #

@router.patch(
    "/{appointment_id}/status",
    response_model=AppointmentRead,
    summary="Advance an appointment through the lifecycle state machine.",
    responses={
        403: {"description": "Not a participant, or wrong role for this transition."},
        404: {"description": "Appointment not found."},
        422: {"description": "Invalid state transition or missing actual_price."},
    },
)
async def update_appointment_status(
    request: Request,
    appointment_id: uuid.UUID,
    payload: AppointmentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppointmentRead:
    """
    Enforces the VALID_TRANSITIONS state machine defined in models.py.

    | From         | To                    | Who                  |
    |--------------|-----------------------|----------------------|
    | PENDING      | CONFIRMED             | detailer / admin     |
    | PENDING      | CANCELLED_BY_*        | client / detailer    |
    | CONFIRMED    | ARRIVED               | detailer / admin     |
    | CONFIRMED    | IN_PROGRESS           | detailer / admin     |
    | CONFIRMED    | CANCELLED_BY_*        | client / detailer    |
    | ARRIVED      | IN_PROGRESS           | detailer / admin     |
    | IN_PROGRESS  | COMPLETED             | detailer / admin     |
    | IN_PROGRESS  | NO_SHOW               | detailer / admin     |

    `actual_price` (USD cents) is required when transitioning to COMPLETED.
    Lifecycle timestamps (arrived_at, started_at, completed_at) are stamped
    automatically by the service. A WebSocket broadcast is sent to all
    participants in the appointment room after a successful transition.
    """
    svc = AppointmentService(db)
    updated = await svc.transition_status(
        appointment_id=appointment_id,
        payload=payload,
        actor=current_user,
    )

    # Broadcast status change to all WS participants in this appointment's room
    manager: ConnectionManager = _get_ws_manager(request)
    if manager.room_size(appointment_id) > 0:
        await manager.broadcast(
            appointment_id,
            {
                "type": "status_change",
                "status": updated.status.value,
                "appointment_id": str(appointment_id),
                "ts": datetime.now(timezone.utc).isoformat(),
            },
        )

    return _build_appointment_read(updated)


# ── GET /mine  (paginated list) ───────────────────────────────────── #

@router.get(
    "/mine",
    response_model=dict,
    summary="Paginated appointments for the authenticated user.",
)
async def list_my_appointments(
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns: { items: [...], total, page, page_size, pages }

    Role-aware branching happens here (not in the service layer):
      CLIENT   → filters by client_id
      DETAILER → filters by detailer_id
    """
    repo   = AppointmentRepository(db)
    offset = (page - 1) * page_size

    if current_user.is_detailer():
        items, total = await repo.get_by_detailer(
            current_user.id, offset=offset, limit=page_size
        )
    else:
        items, total = await repo.get_by_client(
            current_user.id, offset=offset, limit=page_size
        )

    return PaginatedResponse.build(
        items=[_build_appointment_read(a).model_dump(by_alias=True) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    ).model_dump()


# ── GET /{id}  (single, participant-gated) ────────────────────────── #

@router.get(
    "/{appointment_id}",
    response_model=AppointmentRead,
    summary="Fetch a single appointment (participant or admin only).",
    responses={
        403: {"description": "Not a participant in this appointment."},
        404: {"description": "Appointment not found."},
    },
)
async def get_appointment(
    appointment_id: uuid.UUID,  # FastAPI coerces str→UUID natively; no try/except needed
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppointmentRead:
    """
    Access control: only the client, the assigned detailer, or an ADMIN
    may fetch this record. Prevents IDOR across clients.
    """
    repo        = AppointmentRepository(db)
    appointment = await repo.get_by_id(appointment_id)

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' not found.",
        )

    is_participant = (
        appointment.client_id   == current_user.id
        or appointment.detailer_id == current_user.id
    )
    if not is_participant and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorised to view this appointment.",
        )

    return _build_appointment_read(appointment)