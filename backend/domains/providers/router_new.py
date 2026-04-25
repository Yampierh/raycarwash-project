from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from infrastructure.db.session import get_db
from app.models.models import (
    Appointment, AppointmentStatus, AuditAction,
    ProviderProfile, ProviderSpecialty, Specialty,
    DetailerService, Service, User, VehicleSize,
)
from app.repositories.appointment_repository import AppointmentRepository
from domains.audit.repository import AuditRepository
from domains.providers.repository import ProviderRepository
from domains.providers.schemas import (
    DetailerMeRead, ProviderProfileCreate, ProviderProfileRead,
    DetailerPublicRead, DetailerServiceRead, DetailerServiceUpdate, DetailerStatusUpdate,
    LocationResponse, LocationUpdate,
)
from domains.matching.schemas import TimeSlotRead
from shared.schemas import PaginatedResponse
from app.services.appointment_service import AppointmentService
from app.services.auth import get_current_user, require_role

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/detailers", tags=["Detailers"])


async def _sync_specialties(profile, slugs, db):
    await db.execute(delete(ProviderSpecialty).where(ProviderSpecialty.provider_profile_id == profile.id))
    if slugs:
        result = await db.execute(select(Specialty).where(Specialty.slug.in_(slugs)))
        for sp in result.scalars().all():
            db.add(ProviderSpecialty(provider_profile_id=profile.id, specialty_id=sp.id))
    await db.flush()
    await db.refresh(profile, attribute_names=["specialties_rel"])


async def _compute_detailer_stats(detailer_user_id, db):
    stmt = select(
        func.coalesce(func.sum(Appointment.actual_price), 0).label("earnings"),
        func.count(Appointment.id).label("count"),
    ).where(Appointment.detailer_id == detailer_user_id, Appointment.status == AppointmentStatus.COMPLETED, Appointment.is_deleted.is_(False))
    row = (await db.execute(stmt)).one()
    return int(row.earnings), int(row.count)
