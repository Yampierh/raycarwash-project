# app/routers/detailer_router.py  —  Sprint 6 (frontend contract)
#
# Endpoints:
#   GET  /api/v1/detailers                          — public discovery
#   GET  /api/v1/detailers/me                       — detailer's own profile + stats
#   PUT  /api/v1/detailers/me                       — upsert own profile
#   PATCH /api/v1/detailers/me/status               — toggle is_accepting_bookings
#   GET  /api/v1/detailers/me/services              — list all platform services w/ detailer state
#   PATCH /api/v1/detailers/me/services/{service_id} — toggle service + set custom price
#   GET  /api/v1/detailers/{id}/availability        — public availability slots
#   POST /api/v1/detailers/location                 — GPS update
#   GET  /api/v1/detailers/{id}/profile             — public profile (legacy)

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import (
    Appointment,
    AppointmentStatus,
    AuditAction,
    DetailerProfile,
    DetailerService,
    Service,
    User,
    UserRole,
    VehicleSize,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.detailer_repository import DetailerRepository
from app.schemas.schemas import (
    DetailerMeRead,
    DetailerProfileCreate,
    DetailerProfileRead,
    DetailerProfileUpdate,
    DetailerPublicRead,
    DetailerServiceRead,
    DetailerServiceUpdate,
    DetailerStatusUpdate,
    LocationResponse,
    LocationUpdate,
    PaginatedResponse,
    TimeSlotRead,
)
from app.services.appointment_service import AppointmentService
from app.services.auth import get_current_user, require_role

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/detailers", tags=["Detailers"])


# ================================================================== #
#  Public: Discovery                                                  #
# ================================================================== #

@router.get(
    "",
    response_model=dict,
    summary="Search available detailers.",
)
async def list_detailers(
    lat: float | None = Query(default=None, ge=-90.0, le=90.0),
    lng: float | None = Query(default=None, ge=-180.0, le=180.0),
    radius_miles: float = Query(default=25.0, ge=1.0, le=100.0),
    min_rating: float | None = Query(default=None, ge=1.0, le=5.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if (lat is None) != (lng is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lat and lng must be provided together or both omitted.",
        )
    repo = DetailerRepository(db)
    rows, total = await repo.list_available(
        lat=lat, lng=lng, radius_miles=radius_miles,
        min_rating=min_rating, page=page, page_size=page_size,
    )
    items = [
        DetailerPublicRead(
            user_id=row["user"].id,
            full_name=row["user"].full_name,
            bio=row["profile"].bio,
            years_of_experience=row["profile"].years_of_experience,
            service_radius_miles=row["profile"].service_radius_miles,
            is_accepting_bookings=row["profile"].is_accepting_bookings,
            average_rating=float(row["profile"].average_rating) if row["profile"].average_rating else None,
            total_reviews=row["profile"].total_reviews,
            distance_miles=round(row["distance_miles"], 2) if row["distance_miles"] is not None else None,
        )
        for row in rows
    ]
    return PaginatedResponse.build(
        items=[i.model_dump() for i in items],
        total=total, page=page, page_size=page_size,
    ).model_dump()


# ================================================================== #
#  Private: Own profile (must be registered before /{detailer_id})   #
# ================================================================== #

@router.get(
    "/me",
    response_model=DetailerMeRead,
    summary="Get the authenticated detailer's profile with stats.",
    responses={
        404: {"description": "Profile not found — call PUT /me to create it."},
    },
)
async def get_my_profile(
    current_user: User = Depends(require_role(UserRole.DETAILER)),
    db: AsyncSession = Depends(get_db),
) -> DetailerMeRead:
    """Returns full profile including computed stats (earnings, service count)."""
    repo    = DetailerRepository(db)
    profile = await repo.get_profile(current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No detailer profile found. Create one via PUT /api/v1/detailers/me.",
        )

    # Compute stats from appointments
    total_earnings_cents, total_services = await _compute_detailer_stats(
        current_user.id, db
    )

    return DetailerMeRead(
        user_id=current_user.id,
        full_name=current_user.full_name,
        bio=profile.bio,
        years_of_experience=profile.years_of_experience,
        service_radius_miles=profile.service_radius_miles,
        is_accepting_bookings=profile.is_accepting_bookings,
        average_rating=float(profile.average_rating) if profile.average_rating else None,
        total_reviews=profile.total_reviews,
        total_earnings_cents=total_earnings_cents,
        total_services=total_services,
        specialties=profile.specialties or [],
        created_at=profile.created_at,
    )


@router.put(
    "/me",
    response_model=DetailerMeRead,
    summary="Create or update the authenticated detailer's profile (upsert).",
)
async def upsert_my_profile(
    payload: DetailerProfileCreate,
    current_user: User = Depends(require_role(UserRole.DETAILER)),
    db: AsyncSession = Depends(get_db),
) -> DetailerMeRead:
    """
    Upsert semantics: creates profile on first call, updates on subsequent calls.
    Used by both the Onboarding screen and the Edit Profile screen.
    """
    repo    = DetailerRepository(db)
    profile = await repo.get_profile(current_user.id)

    working_hours_dict = (
        {day: cfg.model_dump() for day, cfg in payload.working_hours.items()}
        if payload.working_hours
        else {
            "monday":    {"start": "08:00", "end": "18:00", "enabled": True},
            "tuesday":   {"start": "08:00", "end": "18:00", "enabled": True},
            "wednesday": {"start": "08:00", "end": "18:00", "enabled": True},
            "thursday":  {"start": "08:00", "end": "18:00", "enabled": True},
            "friday":    {"start": "08:00", "end": "18:00", "enabled": True},
            "saturday":  {"start": "09:00", "end": "16:00", "enabled": True},
            "sunday":    {"start": None,    "end": None,    "enabled": False},
        }
    )

    if profile is None:
        # CREATE
        profile = DetailerProfile(
            user_id=current_user.id,
            bio=payload.bio,
            years_of_experience=payload.years_of_experience,
            service_radius_miles=payload.service_radius_miles,
            timezone=payload.timezone,
            working_hours=working_hours_dict,
            is_accepting_bookings=True,
        )
        profile = await repo.create_profile(profile)
        await AuditRepository(db).log(
            action=AuditAction.DETAILER_PROFILE_CREATED,
            entity_type="detailer_profile",
            entity_id=str(profile.id),
            actor_id=current_user.id,
            metadata={"timezone": payload.timezone},
        )
        logger.info("DetailerProfile created | user=%s", current_user.id)
    else:
        # UPDATE
        fields: dict = {
            "bio": payload.bio,
            "years_of_experience": payload.years_of_experience,
            "service_radius_miles": payload.service_radius_miles,
            "timezone": payload.timezone,
            "working_hours": working_hours_dict,
        }
        profile = await repo.update_profile(current_user.id, fields)
        await AuditRepository(db).log(
            action=AuditAction.DETAILER_PROFILE_UPDATED,
            entity_type="detailer_profile",
            entity_id=str(profile.id),
            actor_id=current_user.id,
            metadata={"updated_fields": list(fields.keys())},
        )
        logger.info("DetailerProfile updated | user=%s", current_user.id)

    total_earnings_cents, total_services = await _compute_detailer_stats(
        current_user.id, db
    )

    return DetailerMeRead(
        user_id=current_user.id,
        full_name=current_user.full_name,
        bio=profile.bio,
        years_of_experience=profile.years_of_experience,
        service_radius_miles=profile.service_radius_miles,
        is_accepting_bookings=profile.is_accepting_bookings,
        average_rating=float(profile.average_rating) if profile.average_rating else None,
        total_reviews=profile.total_reviews,
        total_earnings_cents=total_earnings_cents,
        total_services=total_services,
        specialties=profile.specialties or [],
        created_at=profile.created_at,
    )


@router.patch(
    "/me/status",
    status_code=status.HTTP_200_OK,
    summary="Toggle the detailer's accepting-bookings status.",
)
async def update_accepting_status(
    payload: DetailerStatusUpdate,
    current_user: User = Depends(require_role(UserRole.DETAILER)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Activates or deactivates the detailer's visibility in matching/discovery."""
    repo    = DetailerRepository(db)
    profile = await repo.get_profile(current_user.id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No detailer profile found. Create one via PUT /api/v1/detailers/me.",
        )

    await repo.update_profile(
        current_user.id,
        {"is_accepting_bookings": payload.is_accepting_bookings},
    )
    logger.info(
        "Detailer status toggled | user=%s accepting=%s",
        current_user.id, payload.is_accepting_bookings,
    )
    return {}


# ================================================================== #
#  Private: Service management                                        #
# ================================================================== #

@router.get(
    "/me/services",
    response_model=list[DetailerServiceRead],
    summary="List all platform services with the detailer's own state.",
)
async def list_my_services(
    current_user: User = Depends(require_role(UserRole.DETAILER)),
    db: AsyncSession = Depends(get_db),
) -> list[DetailerServiceRead]:
    """
    Returns ALL active platform services.
    For each service, looks up the detailer's own record (is_active, custom_price_cents).
    If no record exists yet, the service is shown as inactive with no custom price.
    """
    profile = await DetailerRepository(db).get_profile(current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No detailer profile found. Create one via PUT /api/v1/detailers/me.",
        )

    # All active platform services
    stmt = select(Service).where(Service.is_active.is_(True), Service.is_deleted.is_(False))
    result = await db.execute(stmt)
    services = result.scalars().all()

    # Index the detailer's overrides by service_id
    ds_map: dict[uuid.UUID, DetailerService] = {
        ds.service_id: ds for ds in profile.detailer_services
    }

    return [
        DetailerServiceRead(
            service_id=svc.id,
            name=svc.name,
            description=svc.description,
            base_price_cents=svc.base_price_cents,
            custom_price_cents=ds_map[svc.id].custom_price_cents if svc.id in ds_map else None,
            is_active=ds_map[svc.id].is_active if svc.id in ds_map else False,
        )
        for svc in services
    ]


@router.patch(
    "/me/services/{service_id}",
    status_code=status.HTTP_200_OK,
    summary="Toggle a service on/off and optionally set a custom price.",
)
async def update_my_service(
    service_id: uuid.UUID,
    payload: DetailerServiceUpdate,
    current_user: User = Depends(require_role(UserRole.DETAILER)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upserts the detailer's service record.
    - is_active: makes this service bookable by clients.
    - custom_price_cents: null = use platform base price.
    """
    profile = await DetailerRepository(db).get_profile(current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No detailer profile found.",
        )

    # Verify the service exists on the platform
    svc_result = await db.execute(
        select(Service).where(Service.id == service_id, Service.is_active.is_(True))
    )
    if svc_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_id}' not found or inactive.",
        )

    # Upsert DetailerService record
    ds_result = await db.execute(
        select(DetailerService).where(
            DetailerService.detailer_id == profile.id,
            DetailerService.service_id == service_id,
        )
    )
    ds = ds_result.scalar_one_or_none()

    if ds is None:
        ds = DetailerService(
            detailer_id=profile.id,
            service_id=service_id,
            is_active=payload.is_active,
            custom_price_cents=payload.custom_price_cents,
        )
        db.add(ds)
    else:
        ds.is_active = payload.is_active
        ds.custom_price_cents = payload.custom_price_cents

    await db.flush()
    logger.info(
        "DetailerService upserted | detailer=%s service=%s active=%s",
        current_user.id, service_id, payload.is_active,
    )
    return {}


# ================================================================== #
#  Public: Availability                                               #
# ================================================================== #

@router.get(
    "/{detailer_id}/availability",
    response_model=list[TimeSlotRead],
    summary="Get available booking slots for a detailer on a date.",
)
async def get_detailer_availability(
    detailer_id: uuid.UUID,
    request_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    service_id: uuid.UUID | None = Query(default=None),
    vehicle_size: VehicleSize | None = Query(default=None),
    override_duration_minutes: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> list[TimeSlotRead]:
    try:
        parsed_date = date.fromisoformat(request_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="request_date must be YYYY-MM-DD.",
        )
    if parsed_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot query availability for a past date.",
        )
    if service_id is not None and vehicle_size is None and override_duration_minutes is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="vehicle_size or override_duration_minutes is required when service_id is provided.",
        )

    svc   = AppointmentService(db)
    slots = await svc.get_available_slots(
        detailer_id=detailer_id,
        request_date=parsed_date,
        service_id=service_id,
        vehicle_size=vehicle_size,
        override_duration_minutes=override_duration_minutes,
    )
    return [
        TimeSlotRead(start_time=s.start_time, end_time=s.end_time, is_available=s.is_available)
        for s in slots
    ]


# ================================================================== #
#  Private: GPS location update                                       #
# ================================================================== #

@router.post(
    "/location",
    response_model=LocationResponse,
    summary="Update the detailer's current GPS coordinates.",
)
async def update_detailer_location(
    payload: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocationResponse:
    if current_user.role != UserRole.DETAILER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only DETAILER accounts can update location.",
        )
    await DetailerRepository(db).update_location(
        user_id=current_user.id,
        lat=payload.latitude,
        lng=payload.longitude,
    )
    return LocationResponse(
        user_id=current_user.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        updated_at=datetime.now(timezone.utc),
    )


# ================================================================== #
#  Public: Profile by ID (legacy)                                     #
# ================================================================== #

@router.get(
    "/{detailer_id}/profile",
    response_model=DetailerProfileRead,
    summary="Fetch a detailer's public profile.",
)
async def get_detailer_profile(
    detailer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DetailerProfileRead:
    profile = await DetailerRepository(db).get_profile(detailer_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detailer profile for {detailer_id} not found.",
        )
    return DetailerProfileRead.model_validate(profile)


# ================================================================== #
#  Internal helper                                                    #
# ================================================================== #

async def _compute_detailer_stats(
    detailer_user_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[int, int]:
    """
    Returns (total_earnings_cents, total_services) for a detailer.
    Counts only COMPLETED appointments.
    """
    stmt = select(
        func.coalesce(func.sum(Appointment.actual_price), 0).label("earnings"),
        func.count(Appointment.id).label("count"),
    ).where(
        Appointment.detailer_id == detailer_user_id,
        Appointment.status == AppointmentStatus.COMPLETED,
        Appointment.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    row = result.one()
    return int(row.earnings), int(row.count)
