# app/db/detailer_seed.py
#
# Test seed: 6 realistic detailers in Fort Wayne, IN.
# Each detailer gets:
#   - A User row with 'detailer' role (via RBAC)
#   - A DetailerProfile row (bio, working_hours, timezone, location)
#   - A set of active services with some custom prices
#
# Idempotent: keyed on email — safe to call on every startup.
# Call order: must run AFTER seed_rbac() and seed_services().

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from math import ceil
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    DetailerProfile,
    DetailerService,
    Role,
    Service,
    User,
    UserRoleAssociation,
)
from app.services.auth import AuthService

logger = logging.getLogger(__name__)

# ── Fort Wayne, IN bounding box ────────────────────────────────────── #
# City center: 41.0793° N, -85.1394° W
# Detailers are scattered across the metro area.

DETAILERS: list[dict[str, Any]] = [
    # ---------------------------------------------------------------- #
    {
        "email": "ray.martinez@raycarwash.test",
        "full_name": "Ray Martinez",
        "phone_number": "+12605550101",
        "current_lat": 41.0793,
        "current_lng": -85.1394,
        "bio": (
            "Hey! I'm Ray — the founder of RayCarwash. "
            "10+ years detailing cars in Fort Wayne. "
            "I specialise in paint correction and ceramic coatings. "
            "Your car will look better than when you bought it."
        ),
        "years_of_experience": 10,
        "service_radius_miles": 30,
        "average_rating": 4.97,
        "total_reviews": 312,
        "timezone": "America/Indiana/Indianapolis",
        "working_hours": {
            "monday":    {"start": "07:00", "end": "19:00", "enabled": True},
            "tuesday":   {"start": "07:00", "end": "19:00", "enabled": True},
            "wednesday": {"start": "07:00", "end": "19:00", "enabled": True},
            "thursday":  {"start": "07:00", "end": "19:00", "enabled": True},
            "friday":    {"start": "07:00", "end": "19:00", "enabled": True},
            "saturday":  {"start": "08:00", "end": "17:00", "enabled": True},
            "sunday":    {"start": "09:00", "end": "15:00", "enabled": True},
        },
        "specialties": ["ceramic_coating", "paint_correction", "full_detail"],
        "services": ["Express Wash", "Interior Detail", "Diamond Detail",
                     "Paint Correction (1-Step)", "Ceramic Coating (Entry)"],
        "custom_prices": {
            "Ceramic Coating (Entry)": 27_900,  # $279 vs $299 platform
        },
    },
    # ---------------------------------------------------------------- #
    {
        "email": "sofia.chen@raycarwash.test",
        "full_name": "Sofia Chen",
        "phone_number": "+12605550102",
        "current_lat": 41.1251,
        "current_lng": -85.1027,
        "bio": (
            "Mobile detailer serving North Fort Wayne and Huntertown. "
            "Eco-friendly waterless products for driveways without drainage. "
            "Mom of two — I know how messy family SUVs can get! "
            "5-star service guaranteed or your money back."
        ),
        "years_of_experience": 4,
        "service_radius_miles": 20,
        "average_rating": 4.85,
        "total_reviews": 87,
        "timezone": "America/Indiana/Indianapolis",
        "working_hours": {
            "monday":    {"start": "08:00", "end": "17:00", "enabled": True},
            "tuesday":   {"start": "08:00", "end": "17:00", "enabled": True},
            "wednesday": {"start": None,    "end": None,    "enabled": False},
            "thursday":  {"start": "08:00", "end": "17:00", "enabled": True},
            "friday":    {"start": "08:00", "end": "17:00", "enabled": True},
            "saturday":  {"start": "09:00", "end": "14:00", "enabled": True},
            "sunday":    {"start": None,    "end": None,    "enabled": False},
        },
        "specialties": ["interior_detail", "family_vehicles", "eco_friendly"],
        "services": ["Express Wash", "Interior Detail", "Diamond Detail"],
        "custom_prices": {
            "Interior Detail": 13_500,  # $135 vs $150 platform
        },
    },
    # ---------------------------------------------------------------- #
    {
        "email": "marcus.johnson@raycarwash.test",
        "full_name": "Marcus Johnson",
        "phone_number": "+12605550103",
        "current_lat": 41.0432,
        "current_lng": -85.0986,
        "bio": (
            "Former body shop technician turned mobile detailer. "
            "I bring the shop to you. "
            "Trucks, SUVs, and work vehicles are my specialty — "
            "I get into every crevice. Southwest Fort Wayne area."
        ),
        "years_of_experience": 7,
        "service_radius_miles": 25,
        "average_rating": 4.78,
        "total_reviews": 143,
        "timezone": "America/Indiana/Indianapolis",
        "working_hours": {
            "monday":    {"start": "06:00", "end": "16:00", "enabled": True},
            "tuesday":   {"start": "06:00", "end": "16:00", "enabled": True},
            "wednesday": {"start": "06:00", "end": "16:00", "enabled": True},
            "thursday":  {"start": "06:00", "end": "16:00", "enabled": True},
            "friday":    {"start": "06:00", "end": "16:00", "enabled": True},
            "saturday":  {"start": "07:00", "end": "15:00", "enabled": True},
            "sunday":    {"start": None,    "end": None,    "enabled": False},
        },
        "specialties": ["trucks", "full_detail", "engine_bay"],
        "services": ["Express Wash", "Interior Detail", "Diamond Detail",
                     "Engine Bay Cleaning"],
        "custom_prices": {
            "Engine Bay Cleaning": 6_500,   # $65 vs $75 platform
            "Diamond Detail":      22_000,  # $220 vs $250 platform
        },
    },
    # ---------------------------------------------------------------- #
    {
        "email": "priya.patel@raycarwash.test",
        "full_name": "Priya Patel",
        "phone_number": "+12605550104",
        "current_lat": 41.0682,
        "current_lng": -85.1720,
        "bio": (
            "Detail artist and car enthusiast. "
            "Certified IDA detailer with a passion for luxury and exotic vehicles. "
            "Paint protection film installation and ceramic coating specialist. "
            "West Fort Wayne / Coventry area."
        ),
        "years_of_experience": 6,
        "service_radius_miles": 20,
        "average_rating": 4.93,
        "total_reviews": 201,
        "timezone": "America/Indiana/Indianapolis",
        "working_hours": {
            "monday":    {"start": "09:00", "end": "18:00", "enabled": True},
            "tuesday":   {"start": "09:00", "end": "18:00", "enabled": True},
            "wednesday": {"start": "09:00", "end": "18:00", "enabled": True},
            "thursday":  {"start": "09:00", "end": "18:00", "enabled": True},
            "friday":    {"start": "09:00", "end": "18:00", "enabled": True},
            "saturday":  {"start": "10:00", "end": "16:00", "enabled": True},
            "sunday":    {"start": None,    "end": None,    "enabled": False},
        },
        "specialties": ["luxury_vehicles", "ceramic_coating", "paint_correction"],
        "services": ["Express Wash", "Interior Detail", "Diamond Detail",
                     "Paint Correction (1-Step)", "Ceramic Coating (Entry)"],
        "custom_prices": {
            "Paint Correction (1-Step)": 22_900,  # $229 vs $199 (premium positioning)
            "Ceramic Coating (Entry)":   34_900,  # $349 vs $299
        },
    },
    # ---------------------------------------------------------------- #
    {
        "email": "derek.williams@raycarwash.test",
        "full_name": "Derek Williams",
        "phone_number": "+12605550105",
        "current_lat": 41.1098,
        "current_lng": -85.1831,
        "bio": (
            "Weekend warrior turned full-time detailer. "
            "Budget-friendly options for everyone — no job too small. "
            "Fast turnaround, reliable service, Northwest side. "
            "Fleet discounts available for businesses."
        ),
        "years_of_experience": 2,
        "service_radius_miles": 15,
        "average_rating": 4.61,
        "total_reviews": 55,
        "timezone": "America/Indiana/Indianapolis",
        "working_hours": {
            "monday":    {"start": None,    "end": None,    "enabled": False},
            "tuesday":   {"start": "10:00", "end": "18:00", "enabled": True},
            "wednesday": {"start": "10:00", "end": "18:00", "enabled": True},
            "thursday":  {"start": "10:00", "end": "18:00", "enabled": True},
            "friday":    {"start": "10:00", "end": "18:00", "enabled": True},
            "saturday":  {"start": "08:00", "end": "18:00", "enabled": True},
            "sunday":    {"start": "10:00", "end": "16:00", "enabled": True},
        },
        "specialties": ["budget_friendly", "express_wash", "fleet"],
        "services": ["Express Wash", "Interior Detail"],
        "custom_prices": {
            "Express Wash":   4_000,   # $40 vs $50 platform
            "Interior Detail": 12_000, # $120 vs $150 platform
        },
    },
    # ---------------------------------------------------------------- #
    {
        "email": "ana.torres@raycarwash.test",
        "full_name": "Ana Torres",
        "phone_number": "+12605550106",
        "current_lat": 41.0581,
        "current_lng": -85.2012,
        "bio": (
            "Bilingual (English/Spanish) mobile detailer. "
            "Specialising in paint decontamination and exterior restoration. "
            "I travel to you — apartments, offices, anywhere. "
            "New to the platform but not to detailing — 5 years pro experience."
        ),
        "years_of_experience": 5,
        "service_radius_miles": 25,
        "average_rating": 4.72,
        "total_reviews": 34,
        "timezone": "America/Indiana/Indianapolis",
        "working_hours": {
            "monday":    {"start": "08:00", "end": "17:00", "enabled": True},
            "tuesday":   {"start": "08:00", "end": "17:00", "enabled": True},
            "wednesday": {"start": "08:00", "end": "17:00", "enabled": True},
            "thursday":  {"start": "08:00", "end": "17:00", "enabled": True},
            "friday":    {"start": "08:00", "end": "17:00", "enabled": True},
            "saturday":  {"start": "09:00", "end": "15:00", "enabled": True},
            "sunday":    {"start": None,    "end": None,    "enabled": False},
        },
        "specialties": ["paint_decontamination", "exterior", "bilingual"],
        "services": ["Express Wash", "Interior Detail", "Diamond Detail",
                     "Paint Decontamination", "Headlight Restoration"],
        "custom_prices": {},
    },
]


async def seed_detailers(db: AsyncSession) -> None:
    """
    Idempotent seed of 6 test detailers in Fort Wayne, IN.
    Keyed on email — calling this multiple times is safe.
    Must be called AFTER seed_services() so platform services exist.
    """
    hashed_pw = AuthService.hash_password("TestP1!")

    # Pre-load all services into a name→object map
    svc_result = await db.execute(select(Service).where(Service.is_active.is_(True)))
    all_services: dict[str, Service] = {s.name: s for s in svc_result.scalars().all()}

    seeded = 0
    for d in DETAILERS:
        # Check if already seeded
        exists = await db.execute(select(User).where(User.email == d["email"]))
        if exists.scalar_one_or_none() is not None:
            logger.debug("Detailer already seeded: %s", d["email"])
            continue

        # Get the 'detailer' role (must exist from seed_rbac)
        role_result = await db.execute(select(Role).where(Role.name == "detailer"))
        detailer_role = role_result.scalar_one_or_none()
        if detailer_role is None:
            logger.error("Role 'detailer' not found — run seed_rbac() first!")
            continue

        # Create user (RBAC: role assigned via user_roles association)
        user = User(
            email=d["email"],
            full_name=d["full_name"],
            phone_number=d["phone_number"],
            password_hash=hashed_pw,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()  # get user.id

        # Assign role via UserRoleAssociation
        user_role = UserRoleAssociation(
            user_id=user.id,
            role_id=detailer_role.id,
        )
        db.add(user_role)

        # Create detailer profile (location now on profile, not user)
        profile = DetailerProfile(
            user_id=user.id,
            bio=d["bio"],
            years_of_experience=d["years_of_experience"],
            service_radius_miles=d["service_radius_miles"],
            is_accepting_bookings=True,
            average_rating=d["average_rating"],
            total_reviews=d["total_reviews"],
            timezone=d["timezone"],
            working_hours=d["working_hours"],
            specialties=d["specialties"],
            current_lat=d["current_lat"],
            current_lng=d["current_lng"],
            last_location_update=datetime.now(timezone.utc),
        )
        db.add(profile)
        await db.flush()  # get profile.id

        # Create DetailerService rows
        custom_prices: dict[str, int] = d.get("custom_prices", {})
        for svc_name in d["services"]:
            svc = all_services.get(svc_name)
            if svc is None:
                logger.warning("Service '%s' not found — skipping for %s", svc_name, d["email"])
                continue
            db.add(DetailerService(
                detailer_id=profile.id,
                service_id=svc.id,
                is_active=True,
                custom_price_cents=custom_prices.get(svc_name),
            ))

        seeded += 1
        logger.info(
            "Seeded detailer: %-25s | ⭐ %.2f (%d reviews) | lat=%.4f lng=%.4f",
            d["full_name"],
            d["average_rating"],
            d["total_reviews"],
            d["current_lat"],
            d["current_lng"],
        )

    await db.commit()
    logger.info("Detailer seed complete — %d new detailer(s) inserted.", seeded)
