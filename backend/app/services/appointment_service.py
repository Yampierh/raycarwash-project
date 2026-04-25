# app/services/appointment_service.py  —  Sprint 3 (final)
#
# CHANGES VS UPLOADED VERSION:
#   - L469: removed `from app.models.models import TERMINAL_STATUSES` inside
#     transition_status() — TERMINAL_STATUSES was already imported at module
#     level (line 8). Inline re-imports shadow the top-level name and confuse
#     static analysers; if the module-level import ever changes, the inline
#     one silently takes precedence.
#   - L490: removed `from datetime import timezone as _tz` inside
#     transition_status() — `timezone` was already imported at module level
#     via `from datetime import date, datetime, timedelta, timezone`.
#     The inline alias `_tz` was masking a perfectly valid module-level name.
#   All other logic is unchanged.

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import ceil
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.db.seed import SIZE_MULTIPLIERS
from app.models.models import (
    Addon,
    Appointment,
    AppointmentAddon,
    AppointmentStatus,
    AppointmentVehicle,
    AuditAction,
    Service,
    TERMINAL_STATUSES,
    VALID_TRANSITIONS,
    User,
    Vehicle,
    VehicleSize,
)
from app.repositories.addon_repository import AddonRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.provider_repository import ProviderRepository
from app.repositories.service_repository import ServiceRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.vehicle_lookup import map_body_to_size
from app.schemas.schemas import AppointmentCreate, AppointmentStatusUpdate

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()

SLOT_GRANULARITY_MINUTES: int = 30
MIN_ADVANCE_BOOKING_MINUTES: int = 60


# ------------------------------------------------------------------ #
#  Value objects                                                      #
# ------------------------------------------------------------------ #

@dataclass(frozen=True)
class AppointmentCalculation:
    price_cents: int
    duration_minutes: int
    estimated_end_time: datetime
    travel_buffer_end_time: datetime
    multiplier: float


@dataclass(frozen=True)
class TimeSlot:
    """
    A 30-minute display slot on the detailer's calendar.

    end_time = start_time + 30 min (display granularity).
    is_available accounts for the full service duration + travel buffer,
    not just the 30-minute display window.
    """
    start_time: datetime
    end_time: datetime
    is_available: bool


# ------------------------------------------------------------------ #
#  AppointmentService                                                 #
# ------------------------------------------------------------------ #

class AppointmentService:

    def __init__(self, db: AsyncSession) -> None:
        self._db              = db
        self._appointment_repo = AppointmentRepository(db)
        self._user_repo        = UserRepository(db)
        self._vehicle_repo     = VehicleRepository(db)
        self._service_repo     = ServiceRepository(db)
        self._detailer_repo    = ProviderRepository(db)
        self._audit_repo       = AuditRepository(db)
        self._addon_repo       = AddonRepository(db)

    # ---------------------------------------------------------------- #
    #  1. calculate_appointment_data                                    #
    # ---------------------------------------------------------------- #

    @staticmethod
    def calculate_appointment_data(
        service: Service,
        vehicle_size: VehicleSize,
        scheduled_time: datetime,
    ) -> AppointmentCalculation:
        """
        Pure pricing + scheduling computation. No I/O.

        FORMULA:
          price_cents      = ceil(service.base_price_cents × SIZE_MULTIPLIERS[size])
          duration_minutes = ceil(service.base_duration_minutes × SIZE_MULTIPLIERS[size])

        VERIFIED SPOT-CHECKS:
          Express Wash   XL: ceil( 5000 × 2.0) = 10,000¢ ($100) /  120 min
          Interior Detail XL: ceil(15000 × 2.0) = 30,000¢ ($300) /  300 min
          Diamond Detail  XL: ceil(25000 × 2.0) = 50,000¢ ($500) /  480 min ← GMC Sierra
        """
        multiplier:       float = SIZE_MULTIPLIERS[vehicle_size.value]
        price_cents:       int  = ceil(service.base_price_cents    * multiplier)
        duration_minutes:  int  = ceil(service.base_duration_minutes * multiplier)
        estimated_end_time     = scheduled_time + timedelta(minutes=duration_minutes)
        travel_buffer_end_time = estimated_end_time + timedelta(
            minutes=settings.TRAVEL_BUFFER_MINUTES
        )

        logger.debug(
            "Pricing | service=%s size=%s mult=%.1f price=%d¢ duration=%dmin",
            service.name, vehicle_size.value, multiplier, price_cents, duration_minutes,
        )

        return AppointmentCalculation(
            price_cents=price_cents,
            duration_minutes=duration_minutes,
            estimated_end_time=estimated_end_time,
            travel_buffer_end_time=travel_buffer_end_time,
            multiplier=multiplier,
        )

    # ---------------------------------------------------------------- #
    #  1b. calculate_multi_appointment_data  (Sprint 5)                #
    # ---------------------------------------------------------------- #

    @staticmethod
    def calculate_multi_appointment_data(
        service: Service,
        vehicles_with_sizes: list[tuple[Vehicle, VehicleSize]],
        addons: list[Addon],
        scheduled_time: datetime,
        travel_buffer_minutes: int,
    ) -> AppointmentCalculation:
        """
        Compute totals for a multi-vehicle + multi-addon appointment.

        total_price    = Σ (service_price per vehicle size) + Σ addon_price
        total_duration = Σ (service_duration per vehicle size) + Σ addon_duration

        Returns an AppointmentCalculation with the combined totals.
        The multiplier field is set to 1.0 (not meaningful for multi-vehicle).
        """
        from app.db.seed import SIZE_MULTIPLIERS

        total_price    = 0
        total_duration = 0

        for _, size in vehicles_with_sizes:
            mult            = SIZE_MULTIPLIERS[size.value]
            total_price    += ceil(service.base_price_cents      * mult)
            total_duration += ceil(service.base_duration_minutes * mult)

        for addon in addons:
            total_price    += addon.price_cents
            total_duration += addon.duration_minutes

        estimated_end_time     = scheduled_time + timedelta(minutes=total_duration)
        travel_buffer_end_time = estimated_end_time + timedelta(minutes=travel_buffer_minutes)

        logger.debug(
            "Multi-pricing | service=%s vehicles=%d addons=%d total=%d¢ duration=%dmin",
            service.name, len(vehicles_with_sizes), len(addons),
            total_price, total_duration,
        )

        return AppointmentCalculation(
            price_cents=total_price,
            duration_minutes=total_duration,
            estimated_end_time=estimated_end_time,
            travel_buffer_end_time=travel_buffer_end_time,
            multiplier=1.0,
        )

    # ---------------------------------------------------------------- #
    #  2. get_available_slots                                           #
    # ---------------------------------------------------------------- #

    async def get_available_slots(
        self,
        detailer_id: uuid.UUID,
        request_date: date,
        service_id: uuid.UUID | None = None,
        vehicle_size: VehicleSize | None = None,
        override_duration_minutes: int | None = None,  # Sprint 5: pre-computed total
    ) -> list[TimeSlot]:
        """
        Generate the 30-minute availability grid for a detailer on a given day.

        ALGORITHM:
          1. Verify detailer exists and is accepting bookings.
          2. Load working hours from ProviderProfile JSONB.
             Return [] if day is disabled.
          3. Determine effective slot width:
             - With service_id + vehicle_size → service_duration + travel_buffer
             - Without → 30 min (display grid only)
          4. Fetch all active (non-terminal) appointments for that day.
          5. Build occupied intervals: [(scheduled_time, travel_buffer_end_time), ...]
          6. For each 30-min grid slot:
             a. Mark unavailable if in the past or within MIN_ADVANCE_BOOKING window.
             b. Mark unavailable if service window extends beyond end of working day.
             c. Mark unavailable if service window overlaps any occupied interval.
          7. Return ALL slots (available + unavailable) for calendar rendering.

        Total: 3 async DB round-trips per call.
        """
        # Step 1 — detailer validation
        detailer = await self._user_repo.get_active_detailer(detailer_id)
        if detailer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detailer '{detailer_id}' not found or is not active.",
            )

        profile = await self._detailer_repo.get_profile(detailer_id)
        if profile is not None and not profile.is_accepting_bookings:
            logger.info("Detailer %s is not accepting bookings", detailer_id)
            return []

        # Step 2 — working hours
        working_hours = await self._detailer_repo.get_working_hours(detailer_id)
        day_name  = request_date.strftime("%A").lower()
        day_config = (working_hours or {}).get(
            day_name,
            {"start": "08:00", "end": "18:00", "enabled": True},
        )

        if not day_config.get("enabled", True):
            logger.debug("Detailer %s is off on %s", detailer_id, day_name)
            return []

        start_str = day_config.get("start") or "08:00"
        end_str   = day_config.get("end")   or "18:00"
        start_h, start_m = map(int, start_str.split(":"))
        end_h,   end_m   = map(int, end_str.split(":"))

        # Sprint 4: timezone-aware conversion.
        # HH:MM times are stored in the detailer's local timezone (IANA string
        # in ProviderProfile.timezone). We create aware datetimes in that zone
        # then convert to UTC for all downstream comparisons.
        detailer_tz_name = (profile.timezone if profile else None) or "America/Indiana/Indianapolis"
        try:
            detailer_tz = ZoneInfo(detailer_tz_name)
        except ZoneInfoNotFoundError:
            logger.warning(
                "Unknown timezone %r for detailer %s — falling back to UTC",
                detailer_tz_name, detailer_id,
            )
            detailer_tz = timezone.utc

        work_start = datetime(
            request_date.year, request_date.month, request_date.day,
            start_h, start_m, tzinfo=detailer_tz,
        ).astimezone(timezone.utc)
        work_end = datetime(
            request_date.year, request_date.month, request_date.day,
            end_h, end_m, tzinfo=detailer_tz,
        ).astimezone(timezone.utc)

        # Step 3 — effective slot width
        # Sprint 5: if the caller pre-computed a total duration (multi-vehicle + addons)
        # use that directly; otherwise fall back to service_id + vehicle_size.
        if override_duration_minutes is not None:
            service_duration_minutes = override_duration_minutes + settings.TRAVEL_BUFFER_MINUTES
        elif service_id is not None and vehicle_size is not None:
            svc = await self._service_repo.get_by_id(service_id)
            if svc is not None:
                calc = self.calculate_appointment_data(svc, vehicle_size, work_start)
                service_duration_minutes = calc.duration_minutes + settings.TRAVEL_BUFFER_MINUTES
            else:
                # Service not found — fall back to display-grid granularity
                service_duration_minutes = SLOT_GRANULARITY_MINUTES
        else:
            service_duration_minutes = SLOT_GRANULARITY_MINUTES

        service_duration = timedelta(minutes=service_duration_minutes)

        # Step 4 — existing appointments for this day
        day_start_utc = datetime(
            request_date.year, request_date.month, request_date.day,
            0, 0, tzinfo=timezone.utc,
        )
        existing: list[Appointment] = await self._appointment_repo.get_active_for_detailer_on_date(
            detailer_id=detailer_id,
            day_start=day_start_utc,
            day_end=day_start_utc + timedelta(days=1),
        )

        # Step 5 — occupied intervals
        occupied: list[tuple[datetime, datetime]] = [
            (appt.scheduled_time, appt.travel_buffer_end_time)
            for appt in existing
        ]

        logger.debug(
            "Availability | detailer=%s date=%s occupied=%d work=%s-%s svc_dur=%dmin",
            detailer_id, request_date, len(occupied), start_str, end_str,
            service_duration_minutes,
        )

        # Step 6 — generate grid
        now_utc           = datetime.now(timezone.utc)
        earliest_bookable = now_utc + timedelta(minutes=MIN_ADVANCE_BOOKING_MINUTES)
        slots: list[TimeSlot] = []
        cursor = work_start

        while cursor < work_end:
            display_end      = cursor + timedelta(minutes=SLOT_GRANULARITY_MINUTES)
            service_end      = cursor + service_duration

            # a. Past or too soon
            if cursor <= earliest_bookable:
                slots.append(TimeSlot(cursor, display_end, False))
                cursor = display_end
                continue

            # b. Service window overruns the working day
            if service_end > work_end:
                slots.append(TimeSlot(cursor, display_end, False))
                cursor = display_end
                continue

            # c. Overlap check: cursor < occ_end AND occ_start < service_end
            is_available = not any(
                cursor < occ_end and occ_start < service_end
                for occ_start, occ_end in occupied
            )

            slots.append(TimeSlot(cursor, display_end, is_available))
            cursor = display_end

        available_count = sum(1 for s in slots if s.is_available)
        logger.info(
            "Availability | detailer=%s date=%s total_slots=%d available=%d",
            detailer_id, request_date, len(slots), available_count,
        )
        return slots

    # ---------------------------------------------------------------- #
    #  3. create_appointment  (concurrency-safe)                       #
    # ---------------------------------------------------------------- #

    async def create_appointment(
        self,
        payload: AppointmentCreate,
        client: User,
    ) -> Appointment:
        """
        Validate → advisory lock → overlap check → compute price → persist.

        Supports new multi-vehicle format (payload.vehicles) where each vehicle
        carries its own service_id and addon_ids.  Legacy single-vehicle format
        is normalised to the same structure by the AppointmentCreate validator.

        PRICING FLOW:
          total_price    = Σ ceil(base_price × mult_per_size) + Σ addon.price_cents
          total_duration = Σ ceil(base_dur   × mult_per_size) + Σ addon.duration_minutes
        """
        # Role guards
        if client.is_detailer():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Detailers cannot create client bookings. Use a CLIENT account.",
            )
        if payload.detailer_id == client.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot book yourself as a detailer.",
            )

        # Validate detailer
        detailer = await self._user_repo.get_active_detailer(payload.detailer_id)
        if detailer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detailer '{payload.detailer_id}' not found or unavailable.",
            )

        # payload.vehicles is always set after the model_validator
        vehicle_entries = payload.vehicles or []

        # Collect unique service ids and unique addon ids across all vehicles
        all_service_ids = list({v.service_id for v in vehicle_entries})
        all_addon_ids   = list({aid for v in vehicle_entries for aid in v.addon_ids})

        # Load + cache all services
        service_map: dict[uuid.UUID, Service] = {}
        for sid in all_service_ids:
            svc = await self._service_repo.get_by_id(sid)
            if svc is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Service '{sid}' not found or inactive.",
                )
            service_map[sid] = svc

        # Load + validate all vehicles (IDOR guard)
        vehicle_obj_map: dict[uuid.UUID, Vehicle] = {}
        for entry in vehicle_entries:
            vid = entry.vehicle_id
            if vid in vehicle_obj_map:
                continue
            vehicle = await self._vehicle_repo.get_by_id(vid)
            if vehicle is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Vehicle '{vid}' not found.",
                )
            if vehicle.owner_id != client.id:
                logger.warning(
                    "IDOR attempt: client=%s → vehicle=%s (owner=%s)",
                    client.id, vehicle.id, vehicle.owner_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Vehicle '{vid}' does not belong to your account.",
                )
            vehicle_obj_map[vid] = vehicle

        # Load all addons
        addon_map: dict[uuid.UUID, Addon] = {}
        if all_addon_ids:
            addons = await self._addon_repo.get_many_by_ids(all_addon_ids)
            found_ids = {a.id for a in addons}
            for aid in all_addon_ids:
                if aid not in found_ids:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Addon '{aid}' not found or inactive.",
                    )
            addon_map = {a.id: a for a in addons}

        # Compute per-entry price + duration, then aggregate
        total_price_cents = 0
        total_duration_mins = 0
        per_entry_calcs: list[tuple] = []  # (vehicle, size, service, addons, price, duration)

        for entry in vehicle_entries:
            vehicle = vehicle_obj_map[entry.vehicle_id]
            size    = map_body_to_size(vehicle.body_class)
            svc     = service_map[entry.service_id]
            mult    = SIZE_MULTIPLIERS[size.value]
            p       = ceil(svc.base_price_cents      * mult)
            d       = ceil(svc.base_duration_minutes * mult)
            entry_addons = [addon_map[aid] for aid in entry.addon_ids if aid in addon_map]
            for addon in entry_addons:
                p += addon.price_cents
                d += addon.duration_minutes
            total_price_cents   += p
            total_duration_mins += d
            per_entry_calcs.append((vehicle, size, svc, entry_addons, p, d))

        # Build overall timing from total duration
        estimated_end_time     = payload.scheduled_time + timedelta(minutes=total_duration_mins)
        travel_buffer_end_time = estimated_end_time + timedelta(minutes=settings.TRAVEL_BUFFER_MINUTES)

        # Advisory lock → overlap check
        await self._appointment_repo.acquire_detailer_lock(payload.detailer_id)
        conflict_count = await self._appointment_repo.get_overlapping_count(
            detailer_id=payload.detailer_id,
            new_start=payload.scheduled_time,
            new_buffer_end=travel_buffer_end_time,
        )
        if conflict_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Detailer unavailable. Required window: "
                    f"{payload.scheduled_time.isoformat()} → "
                    f"{travel_buffer_end_time.isoformat()}. "
                    "Please choose a different time."
                ),
            )

        # Persist appointment
        first_vehicle = per_entry_calcs[0][0]
        first_service = per_entry_calcs[0][2]
        appointment = Appointment(
            client_id=client.id,
            detailer_id=payload.detailer_id,
            vehicle_id=first_vehicle.id,
            service_id=first_service.id,
            scheduled_time=payload.scheduled_time,
            estimated_end_time=estimated_end_time,
            travel_buffer_end_time=travel_buffer_end_time,
            status=AppointmentStatus.PENDING,
            estimated_price=total_price_cents,
            actual_price=None,
            client_notes=payload.client_notes,
            service_address=payload.service_address,
            service_latitude=payload.service_latitude,
            service_longitude=payload.service_longitude,
        )
        created = await self._appointment_repo.create(appointment)

        # Persist vehicle + addon snapshots
        for vehicle, size, svc, entry_addons, p, d in per_entry_calcs:
            mult = SIZE_MULTIPLIERS[size.value]
            self._db.add(AppointmentVehicle(
                appointment_id=created.id,
                vehicle_id=vehicle.id,
                vehicle_size=size,
                price_cents=ceil(svc.base_price_cents      * mult),
                duration_minutes=ceil(svc.base_duration_minutes * mult),
            ))
            for addon in entry_addons:
                self._db.add(AppointmentAddon(
                    appointment_id=created.id,
                    addon_id=addon.id,
                    price_cents=addon.price_cents,
                    duration_minutes=addon.duration_minutes,
                ))

        await self._db.flush()
        await self._db.refresh(created)

        await self._audit_repo.log(
            action=AuditAction.APPOINTMENT_CREATED,
            entity_type="appointment",
            entity_id=str(created.id),
            actor_id=client.id,
            metadata={
                "vehicles":         [str(e.vehicle_id) for e in vehicle_entries],
                "price_cents":      total_price_cents,
                "duration_minutes": total_duration_mins,
            },
        )

        logger.info(
            "Appointment created | id=%s client=%s detailer=%s "
            "vehicles=%d price=%d¢ duration=%dmin scheduled=%s",
            created.id, client.id, payload.detailer_id,
            len(per_entry_calcs), total_price_cents,
            total_duration_mins, payload.scheduled_time.isoformat(),
        )

        return created

    # ---------------------------------------------------------------- #
    #  4. transition_status  (state machine)                           #
    # ---------------------------------------------------------------- #

    async def transition_status(
        self,
        appointment_id: uuid.UUID,
        payload: AppointmentStatusUpdate,
        actor: User,
    ) -> Appointment:
        """
        Enforce VALID_TRANSITIONS with role-based gates.
        Stamps started_at / completed_at lifecycle timestamps automatically.

        FIX: removed inline re-imports of TERMINAL_STATUSES and timezone —
        both were already imported at module level.
        """
        appointment = await self._appointment_repo.get_by_id(appointment_id)
        if appointment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment '{appointment_id}' not found.",
            )

        is_participant = (
            appointment.client_id == actor.id
            or appointment.detailer_id == actor.id
        )
        if not is_participant and not actor.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorised to update this appointment.",
            )

        current    = appointment.status
        new_status = payload.status

        # Idempotency: already in desired state
        if current == new_status:
            return appointment

        allowed = VALID_TRANSITIONS.get(current, {})
        if new_status not in allowed:
            # Use module-level TERMINAL_STATUSES (no inline re-import needed)
            terminal_msg = (
                " This appointment is in a terminal state."
                if current in TERMINAL_STATUSES else ""
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Cannot transition '{current.value}' → '{new_status.value}'."
                    f"{terminal_msg} "
                    f"Allowed: {[s.value for s in allowed.keys()] or 'none'}."
                ),
            )

        roles_allowed = allowed[new_status]
        if not any(actor.has_role(r) for r in roles_allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Roles {actor.roles!r} cannot trigger "
                    f"'{current.value}' → '{new_status.value}'. "
                    f"Required one of: {sorted(roles_allowed)}."
                ),
            )

        # Lifecycle timestamps — use module-level timezone (no inline import)
        if new_status == AppointmentStatus.COMPLETED:
            appointment.actual_price = payload.actual_price if payload.actual_price is not None else appointment.estimated_price
            appointment.completed_at = datetime.now(timezone.utc)

        if new_status == AppointmentStatus.ARRIVED:
            appointment.arrived_at = datetime.now(timezone.utc)

        if new_status == AppointmentStatus.IN_PROGRESS:
            appointment.started_at = datetime.now(timezone.utc)

        # ---- Cancellation refund policy (Sprint 4) ----
        # Only applies when transitioning from CONFIRMED (payment may have occurred).
        # PENDING cancellations never have a captured payment.
        refund_amount_cents = 0
        refund_policy_applied = "none"
        stripe_refund_id: str | None = None

        is_cancellation = new_status in (
            AppointmentStatus.CANCELLED_BY_CLIENT,
            AppointmentStatus.CANCELLED_BY_DETAILER,
        )
        if (
            is_cancellation
            and current == AppointmentStatus.CONFIRMED
            and appointment.stripe_payment_intent_id
            and not appointment.stripe_payment_intent_id.startswith("pi_stub_NOPAY")
        ):
            hours_until = (
                appointment.scheduled_time - datetime.now(timezone.utc)
            ).total_seconds() / 3600

            if hours_until >= settings.CANCELLATION_FULL_REFUND_HOURS:
                refund_amount_cents   = appointment.estimated_price
                refund_policy_applied = "full"
            elif hours_until >= settings.CANCELLATION_PARTIAL_REFUND_HOURS:
                refund_amount_cents   = int(
                    appointment.estimated_price
                    * settings.CANCELLATION_PARTIAL_REFUND_PERCENT
                    / 100
                )
                refund_policy_applied = "partial"
            # else: <2h → no refund, refund_amount_cents stays 0

            if refund_amount_cents > 0:
                from app.services.payment_service import PaymentService  # avoid circular import
                payment_svc      = PaymentService(self._db)
                stripe_refund_id = await payment_svc.create_refund(
                    payment_intent_id=appointment.stripe_payment_intent_id,
                    amount_cents=refund_amount_cents,
                    reason="requested_by_customer",
                )
                logger.info(
                    "Cancellation refund | appointment=%s policy=%s amount=%d¢ refund=%s",
                    appointment.id, refund_policy_applied,
                    refund_amount_cents, stripe_refund_id,
                )

        old_status         = appointment.status
        appointment.status = new_status

        if payload.detailer_notes is not None:
            appointment.detailer_notes = payload.detailer_notes

        await self._db.flush()
        await self._db.refresh(appointment)

        await self._audit_repo.log(
            action=AuditAction.APPOINTMENT_STATUS_CHANGED,
            entity_type="appointment",
            entity_id=str(appointment.id),
            actor_id=actor.id,
            metadata={
                "from_status":          old_status.value,
                "to_status":            new_status.value,
                "actual_price":         payload.actual_price,
                "refund_policy":        refund_policy_applied,
                "refund_amount_cents":  refund_amount_cents,
                "stripe_refund_id":     stripe_refund_id,
            },
        )

        logger.info(
            "Status change | id=%s %s → %s actor=%s refund=%s(%d¢)",
            appointment.id, old_status.value, new_status.value, actor.id,
            refund_policy_applied, refund_amount_cents,
        )

        # Attach refund metadata to the appointment object so the router
        # can optionally surface it in the response or a separate endpoint.
        appointment.__dict__["_refund_policy"]       = refund_policy_applied
        appointment.__dict__["_refund_amount_cents"] = refund_amount_cents
        appointment.__dict__["_stripe_refund_id"]    = stripe_refund_id

        return appointment