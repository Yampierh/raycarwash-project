# app/routers/matching_router.py  —  Sprint 6 (frontend contract)
#
# GET /api/v1/matching
#
# Frontend contract params:
#   lat, lng            — client coordinates
#   date                — YYYY-MM-DD string
#   service_id          — UUID of the platform service
#   vehicle_sizes       — comma-separated sizes: "small,medium"
#   addon_ids           — comma-separated addon UUIDs (empty string = none)
#
# Response per-detailer:
#   estimated_price     — total price in cents
#   estimated_duration  — total duration in minutes
#   available_slots     — slots for the requested date

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.seed import SIZE_MULTIPLIERS
from app.db.session import get_db
from app.models.models import User, VehicleSize
from app.repositories.addon_repository import AddonRepository
from app.repositories.detailer_repository import DetailerRepository
from app.repositories.service_repository import ServiceRepository
from app.schemas.schemas import MatchingResult, TimeSlotRead
from app.services.appointment_service import AppointmentService
from app.services.auth import get_current_user

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/matching", tags=["Matching"])

_MAX_SLOTS_RETURNED = 5


@router.get(
    "",
    response_model=list[MatchingResult],
    summary="Find detailers compatible with the given service, vehicle sizes, and date.",
)
async def find_matching_detailers(
    lat:           float       = Query(..., ge=-90, le=90,   description="Client latitude."),
    lng:           float       = Query(..., ge=-180, le=180, description="Client longitude."),
    date_str:      str         = Query(..., alias="date", pattern=r"^\d{4}-\d{2}-\d{2}$",
                                       description="Requested date YYYY-MM-DD."),
    service_id:    uuid.UUID   = Query(..., description="Platform service UUID."),
    vehicle_sizes: str         = Query(..., description='Comma-separated sizes: "small,medium"'),
    addon_ids:     str         = Query(default="", description="Comma-separated addon UUIDs."),
    radius_miles:  float       = Query(default=25.0, ge=1, le=100),
    db:            AsyncSession = Depends(get_db),
    current_user:  User         = Depends(get_current_user),
) -> list[MatchingResult]:
    """
    ## Smart Matching

    Returns a ranked list of available detailers for the given date with
    pre-calculated pricing and time slots.

    ### Sorting
    Results are sorted by rating DESC, then distance ASC.
    """
    # ------------------------------------------------------------------ #
    #  Parse + validate inputs                                             #
    # ------------------------------------------------------------------ #
    try:
        request_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date must be YYYY-MM-DD.",
        )

    # Parse vehicle_sizes
    valid_sizes = {v.value for v in VehicleSize}
    parsed_sizes: list[VehicleSize] = []
    for raw in vehicle_sizes.split(","):
        s = raw.strip().lower()
        if not s:
            continue
        if s not in valid_sizes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid vehicle_size '{s}'. Must be one of: {sorted(valid_sizes)}.",
            )
        parsed_sizes.append(VehicleSize(s))

    if not parsed_sizes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one vehicle_size is required.",
        )

    # Parse addon_ids
    parsed_addon_ids: list[uuid.UUID] = []
    if addon_ids.strip():
        for raw in addon_ids.split(","):
            raw = raw.strip()
            if raw:
                try:
                    parsed_addon_ids.append(uuid.UUID(raw))
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid addon UUID: '{raw}'.",
                    )

    # ------------------------------------------------------------------ #
    #  Load service                                                        #
    # ------------------------------------------------------------------ #
    service = await ServiceRepository(db).get_by_id(service_id)
    if service is None or not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_id}' not found or inactive.",
        )

    # ------------------------------------------------------------------ #
    #  Load addons                                                         #
    # ------------------------------------------------------------------ #
    addons = []
    if parsed_addon_ids:
        addons = await AddonRepository(db).get_many_by_ids(parsed_addon_ids)
        found_ids = {a.id for a in addons}
        for aid in parsed_addon_ids:
            if aid not in found_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Addon '{aid}' not found or inactive.",
                )

    # ------------------------------------------------------------------ #
    #  Compute total price + duration                                      #
    # ------------------------------------------------------------------ #
    total_price_cents   = 0
    total_duration_mins = 0

    for size in parsed_sizes:
        mult = SIZE_MULTIPLIERS[size.value]
        total_price_cents   += ceil(service.base_price_cents      * mult)
        total_duration_mins += ceil(service.base_duration_minutes * mult)

    for addon in addons:
        total_price_cents   += addon.price_cents
        total_duration_mins += addon.duration_minutes

    # ------------------------------------------------------------------ #
    #  Find nearby detailers                                               #
    # ------------------------------------------------------------------ #
    detailer_repo = DetailerRepository(db)
    nearby, _ = await detailer_repo.list_available(
        lat=lat, lng=lng, radius_miles=radius_miles,
        page=1, page_size=50,
    )

    if not nearby:
        return []

    # ------------------------------------------------------------------ #
    #  Per-detailer availability                                           #
    # ------------------------------------------------------------------ #
    appt_svc = AppointmentService(db)
    results: list[MatchingResult] = []

    for row in nearby:
        detailer_user    = row["user"]
        detailer_profile = row["profile"]
        distance         = row["distance_miles"]

        try:
            slots = await appt_svc.get_available_slots(
                detailer_id=detailer_user.id,
                request_date=request_date,
                override_duration_minutes=total_duration_mins,
            )
        except HTTPException:
            continue

        available = [s for s in slots if s.is_available]
        if not available:
            continue

        results.append(MatchingResult(
            user_id=detailer_user.id,
            full_name=detailer_user.full_name,
            bio=detailer_profile.bio,
            years_of_experience=detailer_profile.years_of_experience,
            service_radius_miles=detailer_profile.service_radius_miles,
            is_accepting_bookings=detailer_profile.is_accepting_bookings,
            average_rating=float(detailer_profile.average_rating) if detailer_profile.average_rating else None,
            total_reviews=detailer_profile.total_reviews,
            distance_miles=round(distance, 2) if distance is not None else None,
            estimated_price=total_price_cents,
            estimated_duration=total_duration_mins,
            available_slots=[
                TimeSlotRead(
                    start_time=s.start_time,
                    end_time=s.end_time,
                    is_available=s.is_available,
                )
                for s in available[:_MAX_SLOTS_RETURNED]
            ],
        ))

    # Sort: rating DESC, distance ASC
    results.sort(key=lambda r: (
        -(r.average_rating or 0.0),
        r.distance_miles or float("inf"),
    ))

    logger.info(
        "Matching | service=%s sizes=%s addons=%d price=%d¢ %dmin "
        "radius=%.1fmi candidates=%d results=%d",
        service.name, vehicle_sizes, len(addons),
        total_price_cents, total_duration_mins,
        radius_miles, len(nearby), len(results),
    )

    return results
