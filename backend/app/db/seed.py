# app/db/seed.py
#
# SIZE_MULTIPLIERS is the single canonical source for both AppointmentService
# (pricing calculations) and the seeder (pre-computing per-size columns).
# Any multiplier change propagates everywhere from this one file.

from __future__ import annotations

import logging
from math import ceil

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Addon, Service, ServiceCategory

logger = logging.getLogger(__name__)


# ── Business constants ────────────────────────────────────────────── #
# Imported by AppointmentService — do NOT move to another module.

SIZE_MULTIPLIERS: dict[str, float] = {
    "small":  1.0,   # Sedan / Coupe  (e.g. Kia K5 GT-Line)
    "medium": 1.2,   # SUV / Crossover
    "large":  1.5,   # Truck / Full-size SUV
    "xl":     2.0,   # Van / Sprinter / GMC Sierra
}

# Canonical catalogue — base prices/durations are for SMALL vehicle.
# Multipliers applied at seed time for pre-computed columns (price_small, etc.)
# and at runtime for matching/pricing calculations.
SERVICE_CATALOG: list[dict] = [
    # ── Basic Wash ──────────────────────────────────────────────────── #
    {
        "name": "Express Wash",
        "description": (
            "Exterior hand wash, wheel cleaning, window wipe-down, "
            "and tire shine. Perfect for weekly maintenance."
        ),
        "category": ServiceCategory.BASIC_WASH,
        "base_price_cents":      5_000,   # $50 small → $100 XL
        "base_duration_minutes": 45,
    },
    {
        "name": "Exterior Detail",
        "description": (
            "Hand wash + clay bar decontamination, iron remover, "
            "paint sealant, tire dressing, and window seal. "
            "Leaves paint glassy and protected for up to 6 months."
        ),
        "category": ServiceCategory.BASIC_WASH,
        "base_price_cents":      9_500,   # $95 small → $190 XL
        "base_duration_minutes": 90,
    },
    # ── Interior Detail ─────────────────────────────────────────────── #
    {
        "name": "Interior Detail",
        "description": (
            "Full interior vacuum, seat shampooing, dashboard wipe-down, "
            "odor elimination, and glass cleaning."
        ),
        "category": ServiceCategory.INTERIOR_DETAIL,
        "base_price_cents":      15_000,  # $150 small → $300 XL
        "base_duration_minutes": 120,
    },
    {
        "name": "Deep Interior Clean",
        "description": (
            "Intensive interior detail including steam cleaning of carpets, "
            "seats, vents, and headliner. Pet hair removal. "
            "Leather conditioning or fabric protectant. "
            "Ideal for high-mileage or heavily used vehicles."
        ),
        "category": ServiceCategory.INTERIOR_DETAIL,
        "base_price_cents":      22_000,  # $220 small → $440 XL
        "base_duration_minutes": 180,
    },
    # ── Full Detail ─────────────────────────────────────────────────── #
    {
        "name": "Diamond Detail",
        "description": (
            "Full exterior + interior detail, clay bar, one-step paint "
            "correction, sealant application, and ceramic spray coat. "
            "The premium RayCarwash experience."
        ),
        "category": ServiceCategory.FULL_DETAIL,
        "base_price_cents":      25_000,  # $250 small → $500 XL
        "base_duration_minutes": 240,
    },
    {
        "name": "Signature Full Detail",
        "description": (
            "Complete interior deep clean + full exterior decontamination, "
            "two-step paint correction, and 12-month sealant. "
            "Our most comprehensive mobile service."
        ),
        "category": ServiceCategory.FULL_DETAIL,
        "base_price_cents":      35_000,  # $350 small → $700 XL
        "base_duration_minutes": 360,
    },
    # ── Paint Correction ────────────────────────────────────────────── #
    {
        "name": "Paint Correction (1-Step)",
        "description": (
            "Single-stage machine polish removes light swirl marks, "
            "water spots, and minor oxidation. "
            "Restores 60–70% of paint clarity. Finished with paint sealant."
        ),
        "category": ServiceCategory.PAINT_CORRECTION,
        "base_price_cents":      19_900,  # $199 small → $398 XL
        "base_duration_minutes": 210,
    },
    {
        "name": "Paint Correction (2-Step)",
        "description": (
            "Two-stage compound + polish removes deeper scratches, "
            "heavy swirl marks, and oxidation. "
            "Restores 85–95% of paint clarity. Finished with 6-month sealant."
        ),
        "category": ServiceCategory.PAINT_CORRECTION,
        "base_price_cents":      32_900,  # $329 small → $658 XL
        "base_duration_minutes": 360,
    },
    # ── Ceramic Coating ─────────────────────────────────────────────── #
    {
        "name": "Ceramic Coating (Entry)",
        "description": (
            "Entry-level 9H ceramic coating applied after a single-stage "
            "paint correction. Provides 1–2 years of hydrophobic protection, "
            "UV resistance, and high gloss. Includes a maintenance kit."
        ),
        "category": ServiceCategory.CERAMIC_COATING,
        "base_price_cents":      29_900,  # $299 small → $598 XL
        "base_duration_minutes": 300,
    },
    {
        "name": "Ceramic Coating (Pro)",
        "description": (
            "Professional-grade multi-layer ceramic coating after two-step "
            "paint correction. 3–5 years protection. Includes annual "
            "maintenance wash and top-up. Certificate of installation."
        ),
        "category": ServiceCategory.CERAMIC_COATING,
        "base_price_cents":      59_900,  # $599 small → $1,198 XL
        "base_duration_minutes": 480,
    },
    # ── Specialty ───────────────────────────────────────────────────── #
    {
        "name": "Paint Decontamination",
        "description": (
            "Iron fallout remover, tar and adhesive dissolvers, "
            "followed by clay bar treatment. "
            "Essential prep before any coating or correction service."
        ),
        "category": ServiceCategory.PAINT_CORRECTION,
        "base_price_cents":      9_500,   # $95 small → $190 XL
        "base_duration_minutes": 90,
    },
    {
        "name": "Engine Bay Cleaning",
        "description": (
            "Careful degreasing and detailing of the engine bay. "
            "Steam or low-pressure rinse removes grease and road grime. "
            "Plastic restorer and silicone dressing applied."
        ),
        "category": ServiceCategory.BASIC_WASH,
        "base_price_cents":      7_500,   # $75 (size doesn't vary much — XL=$150)
        "base_duration_minutes": 60,
    },
    {
        "name": "Headlight Restoration",
        "description": (
            "Wet-sand and machine-polish oxidised/yellowed headlight lenses. "
            "UV sealant applied to slow re-yellowing. "
            "Improves appearance and night-time visibility."
        ),
        "category": ServiceCategory.BASIC_WASH,
        "base_price_cents":      4_900,   # $49 (flat per pair — size matters less)
        "base_duration_minutes": 45,
    },
]


def _prices(base: int) -> dict[str, int]:
    """ceil() ensures revenue is never lost to fractional cents."""
    return {
        "price_small":  ceil(base * SIZE_MULTIPLIERS["small"]),
        "price_medium": ceil(base * SIZE_MULTIPLIERS["medium"]),
        "price_large":  ceil(base * SIZE_MULTIPLIERS["large"]),
        "price_xl":     ceil(base * SIZE_MULTIPLIERS["xl"]),
    }


def _durations(base: int) -> dict[str, int]:
    """ceil() gives the detailer more time, never less."""
    return {
        "duration_small_minutes":  ceil(base * SIZE_MULTIPLIERS["small"]),
        "duration_medium_minutes": ceil(base * SIZE_MULTIPLIERS["medium"]),
        "duration_large_minutes":  ceil(base * SIZE_MULTIPLIERS["large"]),
        "duration_xl_minutes":     ceil(base * SIZE_MULTIPLIERS["xl"]),
    }


# ── Addon catalogue  (Sprint 5) ───────────────────────────────────── #

ADDON_CATALOG: list[dict] = [
    # ── Paint protection / decontamination ──────────────────────────── #
    {
        "name": "Clay Bar Treatment",
        "description": (
            "Removes embedded contaminants (tar, rail dust, industrial fallout) "
            "from the paint surface before polishing. Leaves paint silky smooth."
        ),
        "price_cents":     3_000,   # +$30
        "duration_minutes": 45,
    },
    {
        "name": "Iron Fallout Remover",
        "description": (
            "Chemical decontamination spray that dissolves iron particles "
            "from brake dust and rail dust embedded in clear coat. "
            "Turns purple on contact — visually satisfying and highly effective."
        ),
        "price_cents":     1_500,   # +$15
        "duration_minutes": 20,
    },
    {
        "name": "Ceramic Spray Coat",
        "description": (
            "Entry-level SiO₂ spray ceramic coating applied after a wash. "
            "Adds 3–6 months of hydrophobic protection and gloss."
        ),
        "price_cents":     5_000,   # +$50
        "duration_minutes": 30,
    },
    {
        "name": "Paint Sealant",
        "description": (
            "Synthetic polymer sealant applied over the paint for 6–8 months "
            "of UV protection, gloss enhancement, and water beading. "
            "Great alternative to wax for longevity."
        ),
        "price_cents":     2_500,   # +$25
        "duration_minutes": 25,
    },
    {
        "name": "Carnauba Wax Finish",
        "description": (
            "Hand-applied Brazilian carnauba wax for a warm, deep gloss. "
            "Best on dark-coloured vehicles. Provides 2–3 months protection."
        ),
        "price_cents":     2_000,   # +$20
        "duration_minutes": 30,
    },
    # ── Interior add-ons ────────────────────────────────────────────── #
    {
        "name": "Odor Eliminator",
        "description": (
            "Ozone + enzyme treatment neutralises smoke, pet, and food odours "
            "at the molecular level. Not just a cover-up."
        ),
        "price_cents":     2_000,   # +$20
        "duration_minutes": 20,
    },
    {
        "name": "Pet Hair Removal",
        "description": (
            "Thorough removal of embedded pet hair from seats, carpets, "
            "and trunk area using rubber tools and vacuum. "
            "Add-on to any interior or full detail service."
        ),
        "price_cents":     2_500,   # +$25
        "duration_minutes": 30,
    },
    {
        "name": "Leather Conditioning",
        "description": (
            "Clean + condition all leather surfaces (seats, door panels, "
            "steering wheel) with premium pH-balanced leather conditioner. "
            "Prevents cracking and restores suppleness."
        ),
        "price_cents":     3_000,   # +$30
        "duration_minutes": 25,
    },
    {
        "name": "Fabric Protectant",
        "description": (
            "Scotchgard-type protectant applied to fabric seats and carpets "
            "after cleaning. Repels spills and makes future cleaning easier."
        ),
        "price_cents":     2_000,   # +$20
        "duration_minutes": 20,
    },
    # ── Engine / mechanical ─────────────────────────────────────────── #
    {
        "name": "Engine Bay Clean",
        "description": (
            "Degreasing and detailing of the engine bay — removes grease "
            "and grime, leaves components looking factory-fresh."
        ),
        "price_cents":     4_000,   # +$40
        "duration_minutes": 40,
    },
    # ── Wheels / exterior ───────────────────────────────────────────── #
    {
        "name": "Wheel & Tire Detail",
        "description": (
            "Deep clean of wheel faces, barrels, lug nuts, and wheel wells. "
            "Tire dressing applied for a rich, satin finish. "
            "Iron fallout remover used on brake-dust buildup."
        ),
        "price_cents":     3_500,   # +$35
        "duration_minutes": 35,
    },
    {
        "name": "Headlight Restoration",
        "description": (
            "Wet-sand and polish oxidised/yellowed headlight lenses. "
            "UV sealant applied. Improves appearance and night visibility."
        ),
        "price_cents":     3_500,   # +$35
        "duration_minutes": 35,
    },
    {
        "name": "Door Jamb Detail",
        "description": (
            "Thorough cleaning and dressing of all four door jambs and "
            "trunk jamb — often skipped in standard washes but highly visible "
            "when doors are open."
        ),
        "price_cents":     1_500,   # +$15
        "duration_minutes": 20,
    },
    # ── Glass ───────────────────────────────────────────────────────── #
    {
        "name": "Rain Repellent Glass Coat",
        "description": (
            "Hydrophobic glass treatment (Rain-X equivalent) applied to all "
            "exterior glass. Water beads and clears at highway speeds — "
            "dramatically improves visibility in rain."
        ),
        "price_cents":     2_000,   # +$20
        "duration_minutes": 20,
    },
    # ── Convenience ─────────────────────────────────────────────────── #
    {
        "name": "Express Lane Priority",
        "description": (
            "Jump the queue — detailer arrives within 90 minutes, guaranteed. "
            "Available during business hours only, subject to detailer availability."
        ),
        "price_cents":     1_500,   # +$15 priority fee
        "duration_minutes": 0,
    },
]


async def seed_addons(db: AsyncSession) -> None:
    """Idempotent upsert of the addon catalogue. Safe to call on every startup."""
    seeded = 0
    for entry in ADDON_CATALOG:
        exists = await db.execute(select(Addon).where(Addon.name == entry["name"]))
        if exists.scalar_one_or_none():
            logger.debug("Skip addon (already seeded): %s", entry["name"])
            continue
        db.add(Addon(**entry))
        seeded += 1
        logger.info(
            "Seeded addon: %-25s | +$%.2f | +%dmin",
            entry["name"],
            entry["price_cents"] / 100,
            entry["duration_minutes"],
        )
    await db.commit()
    logger.info("Addon seed complete — %d new addon(s) inserted.", seeded)


async def seed_services(db: AsyncSession) -> None:
    """
    Idempotent upsert of the service catalogue. Safe to call on every startup.

    Pricing audit:
      Diamond Detail XL = ceil(25_000 × 2.0) = 50_000¢ = $500.00 ✓
      Express Wash   XL = ceil( 5_000 × 2.0) = 10_000¢ = $100.00 ✓
    """
    seeded = 0
    for entry in SERVICE_CATALOG:
        exists = await db.execute(select(Service).where(Service.name == entry["name"]))
        if exists.scalar_one_or_none():
            logger.debug("Skip (already seeded): %s", entry["name"])
            continue

        db.add(Service(
            name=entry["name"],
            description=entry["description"],
            category=entry["category"],
            base_price_cents=entry["base_price_cents"],
            base_duration_minutes=entry["base_duration_minutes"],
            **_prices(entry["base_price_cents"]),
            **_durations(entry["base_duration_minutes"]),
        ))
        seeded += 1
        logger.info(
            "Seeded: %-20s | SMALL $%.2f | XL $%.2f | dur SMALL %dmin | XL %dmin",
            entry["name"],
            entry["base_price_cents"] / 100,
            ceil(entry["base_price_cents"] * SIZE_MULTIPLIERS["xl"]) / 100,
            entry["base_duration_minutes"],
            ceil(entry["base_duration_minutes"] * SIZE_MULTIPLIERS["xl"]),
        )

    await db.commit()
    logger.info("Seed complete — %d new service(s) inserted.", seeded)