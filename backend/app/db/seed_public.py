"""
app/db/seed_public.py — Plan 19 (Track 1) seed data for marketing tables.

All four functions are idempotent (skip rows that already exist) and
safe to call on every startup. Data sourced from the prototypes in
`raycarwash/project/src/{sections-b,customer-b,detailers-b,mechanic}.jsx`
and `dash-services.jsx`.

Functions:
  - seed_testimonials   — 8 client + 3 detailer quotes (4 client featured)
  - seed_faq            — ~30 Q&A items across rider/detailer/mechanic/provider
  - seed_coverage_zones — 6 Fort Wayne–area service zones with SVG coords
  - seed_coverage_zips  — 10 ZIPs mapping into the named zones above
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.public.models import (
    ContactSubmission,  # noqa: F401 — registered so create_all builds the table in tests
    CoverageZip,
    CoverageZone,
    FaqCategory,
    FaqItem,
    Testimonial,
    TestimonialRole,
    WaitlistEntry,  # noqa: F401 — same reason
    WaitlistRole,  # noqa: F401 — same reason
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Testimonials
# ═══════════════════════════════════════════════════════════════════════
#
# Source:
#   - sections-b.jsx Testimonials()  (4 client, featured on landing)
#   - customer-b.jsx ReviewsWall()   (4 additional client quotes for /customer)
#   - detailers-b.jsx DetTestimonials() (3 detailer quotes for /detailers)
#
# `featured=True` means the landing page Hero/Testimonials block surfaces
# the quote. Customer + Detailers pages query without the filter.

_TESTIMONIALS: list[dict] = [
    # ── Client (featured on landing) ────────────────────────────────
    {
        "quote": "Booked at 9 a.m., the truck was in my driveway by 11. Insanely convenient.",
        "name": "Maria G.",
        "city": "Fort Wayne, IN",
        "rating": 5,
        "role": TestimonialRole.CLIENT,
        "featured": True,
        "sort_order": 10,
    },
    {
        "quote": "My detailer sent before/after photos through the app. Felt extremely legit.",
        "name": "Derrick P.",
        "city": "Aboite, IN",
        "rating": 5,
        "role": TestimonialRole.CLIENT,
        "featured": True,
        "sort_order": 20,
    },
    {
        "quote": "Full detail on my F-150 — looks better than the day I bought it.",
        "name": "Jonas R.",
        "city": "New Haven, IN",
        "rating": 5,
        "role": TestimonialRole.CLIENT,
        "featured": True,
        "sort_order": 30,
    },
    {
        "quote": "Pricing is transparent up front. No surprise upcharges, no haggling.",
        "name": "Anna L.",
        "city": "Fort Wayne, IN",
        "rating": 5,
        "role": TestimonialRole.CLIENT,
        "featured": True,
        "sort_order": 40,
    },
    # ── Client (additional, customer page ReviewsWall) ──────────────
    {
        "quote": "Set up a monthly recurring detail in 30 seconds. My car is permanently clean now.",
        "name": "Sarah K.",
        "city": "Huntertown, IN",
        "rating": 5,
        "role": TestimonialRole.CLIENT,
        "featured": False,
        "sort_order": 50,
    },
    {
        "quote": "Detailer arrived in a branded truck with everything he needed. Zero hassle from me.",
        "name": "Mike D.",
        "city": "Leo-Cedarville, IN",
        "rating": 5,
        "role": TestimonialRole.CLIENT,
        "featured": False,
        "sort_order": 60,
    },
    {
        "quote": (
            "I had a stain from a coffee spill that I thought would never come out. "
            "It did. The steam cleaning is real."
        ),
        "name": "Priya N.",
        "city": "Fort Wayne, IN",
        "rating": 5,
        "role": TestimonialRole.CLIENT,
        "featured": False,
        "sort_order": 70,
    },
    {
        "quote": "Cancelled an appointment last minute. Full refund, no questions.",
        "name": "Tomás A.",
        "city": "Aboite, IN",
        "rating": 5,
        "role": TestimonialRole.CLIENT,
        "featured": False,
        "sort_order": 80,
    },
    # ── Detailer (detailers page DetTestimonials, all featured) ─────
    {
        "quote": (
            "I left my dealership job in March. By July I was making more, "
            "and I'm home for dinner every night."
        ),
        "name": "Marcus T.",
        "city": None,
        "rating": 5,
        "role": TestimonialRole.DETAILER,
        "meta": "Detailer · 312 jobs · ★ 4.9",
        "featured": True,
        "sort_order": 10,
    },
    {
        "quote": (
            "The app routes me to jobs I would have spent days finding on Facebook. "
            "I just show up and work."
        ),
        "name": "Trey W.",
        "city": None,
        "rating": 5,
        "role": TestimonialRole.DETAILER,
        "meta": "Detailer · 198 jobs · ★ 4.8",
        "featured": True,
        "sort_order": 20,
    },
    {
        "quote": "Same-day payouts changed everything. I don't have to wait two weeks for an invoice to clear.",
        "name": "Jamal R.",
        "city": None,
        "rating": 5,
        "role": TestimonialRole.DETAILER,
        "meta": "Detailer · 421 jobs · ★ 5.0",
        "featured": True,
        "sort_order": 30,
    },
]


async def seed_testimonials(db: AsyncSession) -> None:
    """Idempotent upsert keyed on (name, sort_order) — testimonials don't
    have a natural unique constraint and we want the seed re-runnable
    even if a quote is edited slightly."""
    seeded = 0
    for entry in _TESTIMONIALS:
        existing = await db.execute(
            select(Testimonial).where(
                Testimonial.name == entry["name"],
                Testimonial.sort_order == entry["sort_order"],
                Testimonial.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(Testimonial(**entry))
        seeded += 1
    await db.commit()
    logger.info("Testimonial seed complete — %d new testimonial(s) inserted.", seeded)


# ═══════════════════════════════════════════════════════════════════════
#  FAQ
# ═══════════════════════════════════════════════════════════════════════
#
# Source:
#   - sections-b.jsx FAQ()         — 8 rider items (landing)
#   - customer-b.jsx CustFAQ()     — 8 rider items (customer page, deduped)
#   - detailers-b.jsx DetFAQ()     — 7 detailer items
#   - mechanic.jsx MechFAQ()       — 6 mechanic items
#   - dash-services.jsx ViewHelp() — 5 provider items
#
# Rider entries combine landing + customer FAQs (lightly deduped — kept
# items with distinct wording even when topics overlap, because the
# landing's 8-slot list and the customer's 8-slot list both query
# `?category=rider` and sort_order decides visibility).

_FAQ: list[dict] = [
    # ── Rider (landing + customer page) ─────────────────────────────
    {
        "category": FaqCategory.RIDER,
        "question": "What area do you serve?",
        "answer": (
            "Fort Wayne, IN and surrounding suburbs (Aboite, New Haven, Huntertown, "
            "Leo-Cedarville). We're expanding — drop us a line if you want us in "
            "your neighborhood."
        ),
        "sort_order": 10,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "Do detailers bring their own water and power?",
        "answer": (
            "Yes. Every detailer arrives self-contained: water tanks, generators, "
            "and pro-grade products. You don't need to lift a finger."
        ),
        "sort_order": 20,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "How are detailers vetted?",
        "answer": (
            "Identity verification, background check, and portfolio review before "
            "they take any job. We re-verify annually."
        ),
        "sort_order": 30,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "Is my vehicle insured during service?",
        "answer": (
            "Yes. We carry commercial coverage for damage caused by the detailer "
            "during a service."
        ),
        "sort_order": 40,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "How does payment work?",
        "answer": (
            "You get a flat quote up front. We authorize the card when you book "
            "and only charge once the job is complete."
        ),
        "sort_order": 50,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "What if I'm not satisfied?",
        "answer": (
            "Open a dispute in the app within 48 hours. If the work doesn't meet "
            "the standard, we'll re-do it or refund you."
        ),
        "sort_order": 60,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "Can I tip my detailer?",
        "answer": "Absolutely — 100% of every tip goes to the detailer.",
        "sort_order": 70,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "Do you offer recurring service?",
        "answer": (
            "Yes. Save your vehicle and detailer to schedule weekly, bi-weekly, "
            "or monthly cleans with one tap."
        ),
        "sort_order": 80,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "How much does a typical wash cost?",
        "answer": (
            "Exterior washes start at $49, interior details at $89, full details "
            "at $149. Final price depends on vehicle size (sedan vs SUV vs truck), "
            "condition, and any add-ons. You always see a flat quote before you book."
        ),
        "sort_order": 90,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "Do I need to be home during the service?",
        "answer": (
            "Nope. Plenty of customers leave the keys (or have us work on the car "
            "while it's parked at their office). We'll send you photos and a "
            "notification when it's done."
        ),
        "sort_order": 100,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "How long does a detail take?",
        "answer": (
            "Exterior wash: 45–60 minutes. Interior detail: 1.5–2 hours. "
            "Full detail: 3–4 hours. Add-ons extend by 20–40 minutes each. "
            "We give you a finish-time estimate when you book."
        ),
        "sort_order": 110,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "What happens if it rains?",
        "answer": (
            "We'll reach out 2–3 hours before the appointment to either reschedule "
            "(free) or proceed if you're OK with that. Indoor parking? Service "
            "goes ahead as planned."
        ),
        "sort_order": 120,
    },
    {
        "category": FaqCategory.RIDER,
        "question": "Is my data and payment info safe?",
        "answer": (
            "Yes. Payments are processed by Stripe (PCI-DSS Level 1). We never "
            "store your card number — only a token. Your address is shared with "
            "the detailer only after they accept the job."
        ),
        "sort_order": 130,
    },
    # ── Detailer ────────────────────────────────────────────────────
    {
        "category": FaqCategory.DETAILER,
        "question": "How much does it really cost to join?",
        "answer": (
            "Nothing up front. We deduct a 15% platform fee from each completed "
            "job — that covers payment processing, insurance coverage during "
            "service, dispatch, support, and marketing. You keep the rest, "
            "including 100% of tips."
        ),
        "sort_order": 10,
    },
    {
        "category": FaqCategory.DETAILER,
        "question": "Do I need to be a full-time detailer?",
        "answer": (
            "No. About 30% of our detailers work part-time or weekends only. "
            "Set your hours and we'll route jobs to fit."
        ),
        "sort_order": 20,
    },
    {
        "category": FaqCategory.DETAILER,
        "question": "Can I bring my existing clients?",
        "answer": (
            "Yes. We have a referral code system — anyone you refer who books "
            "through the app gets $20 off and you get a $40 bonus on top of "
            "your usual cut."
        ),
        "sort_order": 30,
    },
    {
        "category": FaqCategory.DETAILER,
        "question": "What about insurance?",
        "answer": (
            "We carry commercial general liability that covers damage caused by "
            "you during a service. Your personal auto policy still covers transit. "
            "We strongly recommend you also carry your own business liability."
        ),
        "sort_order": 40,
    },
    {
        "category": FaqCategory.DETAILER,
        "question": "How fast do I actually get paid?",
        "answer": (
            "Funds initiate transfer the same day a job is marked complete. "
            "Most banks post within 1–2 business days; instant payouts "
            "(eligible debit cards) hit in minutes."
        ),
        "sort_order": 50,
    },
    {
        "category": FaqCategory.DETAILER,
        "question": "Can I decline jobs?",
        "answer": (
            "Always. Decline rate doesn't affect your standing as long as you "
            "don't ghost. The app shows you the full job details before you accept."
        ),
        "sort_order": 60,
    },
    {
        "category": FaqCategory.DETAILER,
        "question": "What happens if a customer disputes the work?",
        "answer": (
            "We use the before/after photos you captured, the timeline of the "
            "job, and the customer's complaint. Most disputes are resolved with "
            "a re-service rather than a refund."
        ),
        "sort_order": 70,
    },
    # ── Mechanic (pre-launch waitlist page) ─────────────────────────
    {
        "category": FaqCategory.MECHANIC,
        "question": "When will mechanic services actually launch?",
        "answer": (
            "Beta in Q4 2026 with our first cohort of founding mechanics. "
            "Public launch in Q1 2027, starting in Fort Wayne and surrounding suburbs."
        ),
        "sort_order": 10,
    },
    {
        "category": FaqCategory.MECHANIC,
        "question": "Will mechanic prices be different from the detailing side?",
        "answer": (
            "Each service has a flat parts-plus-labor price. You'll see the full "
            "quote before booking — no hourly meter, no surprise diagnostic fees."
        ),
        "sort_order": 20,
    },
    {
        "category": FaqCategory.MECHANIC,
        "question": "What if my car needs work I can't get done in a driveway?",
        "answer": (
            "Some jobs (transmission, body work, alignment) need a shop. We'll "
            "diagnose and refer you out — and your diagnostic fee is credited "
            "toward that shop work."
        ),
        "sort_order": 30,
    },
    {
        "category": FaqCategory.MECHANIC,
        "question": "Do you carry the parts on the van?",
        "answer": (
            "Common parts for your make/model are pulled before the appointment. "
            "If we need something obscure, we'll come back the next day with no "
            "second trip fee."
        ),
        "sort_order": 40,
    },
    {
        "category": FaqCategory.MECHANIC,
        "question": "Is your work guaranteed?",
        "answer": (
            "Yes. 12-month or 12,000-mile warranty on parts and labor — whichever "
            "comes first. If something we fixed fails, we come back free."
        ),
        "sort_order": 50,
    },
    {
        "category": FaqCategory.MECHANIC,
        "question": "Can I get on the founding-customer list separately?",
        "answer": (
            "Yes — that's what the waitlist above is. Founding customers get 20% "
            "off their first three appointments and priority booking during beta."
        ),
        "sort_order": 60,
    },
    # ── Provider dashboard help ─────────────────────────────────────
    {
        "category": FaqCategory.PROVIDER,
        "question": "When do payouts arrive?",
        "answer": (
            "Auto-payouts run every Friday at 5pm. Instant payouts arrive in "
            "<30 min for a $0.50 fee."
        ),
        "sort_order": 10,
    },
    {
        "category": FaqCategory.PROVIDER,
        "question": "What's the platform fee?",
        "answer": (
            "15% per completed job. This covers payments, insurance, dispatch, "
            "customer support, and marketing."
        ),
        "sort_order": 20,
    },
    {
        "category": FaqCategory.PROVIDER,
        "question": "How does insurance work?",
        "answer": (
            "Every job is covered up to $2M while you're working through the "
            "platform. Damage claims are filed in-app."
        ),
        "sort_order": 30,
    },
    {
        "category": FaqCategory.PROVIDER,
        "question": "What if a customer cancels?",
        "answer": (
            "If they cancel less than 2 hours before, you get 50% of the ticket "
            "as a cancellation fee."
        ),
        "sort_order": 40,
    },
    {
        "category": FaqCategory.PROVIDER,
        "question": "How do I get more bookings?",
        "answer": (
            "Respond fast (<5 min), keep your rating high, and add good "
            "before/after photos. We surface high responders first."
        ),
        "sort_order": 50,
    },
]


async def seed_faq(db: AsyncSession) -> None:
    """Idempotent upsert keyed on (category, question)."""
    seeded = 0
    for entry in _FAQ:
        existing = await db.execute(
            select(FaqItem).where(
                FaqItem.category == entry["category"],
                FaqItem.question == entry["question"],
                FaqItem.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(FaqItem(**entry))
        seeded += 1
    await db.commit()
    logger.info("FAQ seed complete — %d new FAQ item(s) inserted.", seeded)


# ═══════════════════════════════════════════════════════════════════════
#  Coverage zones (SVG map for Landing.tsx)
# ═══════════════════════════════════════════════════════════════════════
#
# Source: sections-b.jsx Coverage() — 100×100 viewBox coordinates.

_COVERAGE_ZONES: list[dict] = [
    {"name": "Fort Wayne",     "is_primary": True,  "svg_cx": 50, "svg_cy": 50, "svg_r": 12, "sort_order": 10},
    {"name": "Aboite",         "is_primary": False, "svg_cx": 30, "svg_cy": 58, "svg_r": 6,  "sort_order": 20},
    {"name": "Huntertown",     "is_primary": False, "svg_cx": 48, "svg_cy": 28, "svg_r": 5,  "sort_order": 30},
    {"name": "Leo-Cedarville", "is_primary": False, "svg_cx": 68, "svg_cy": 30, "svg_r": 5,  "sort_order": 40},
    {"name": "New Haven",      "is_primary": False, "svg_cx": 70, "svg_cy": 56, "svg_r": 6,  "sort_order": 50},
    {"name": "Waynedale",      "is_primary": False, "svg_cx": 40, "svg_cy": 70, "svg_r": 4,  "sort_order": 60},
]


async def seed_coverage_zones(db: AsyncSession) -> None:
    """Idempotent upsert keyed on zone name (UNIQUE in the schema)."""
    seeded = 0
    for entry in _COVERAGE_ZONES:
        existing = await db.execute(
            select(CoverageZone).where(
                CoverageZone.name == entry["name"],
                CoverageZone.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(CoverageZone(**entry))
        seeded += 1
    await db.commit()
    logger.info("Coverage zones seed complete — %d new zone(s) inserted.", seeded)


# ═══════════════════════════════════════════════════════════════════════
#  Coverage ZIPs (ZIP → zone lookup for POST /coverage/check)
# ═══════════════════════════════════════════════════════════════════════
#
# Plan 19 §4 calls out: 46802, 46804, 46805, 46807, 46815. Extended below
# to cover the named zones above. eta_min is the rough "first-job-of-day"
# arrival window used by the public response.

_COVERAGE_ZIPS: list[dict] = [
    {"zip": "46802", "zone_name": "Fort Wayne",     "eta_min": 22},
    {"zip": "46805", "zone_name": "Fort Wayne",     "eta_min": 22},
    {"zip": "46808", "zone_name": "Fort Wayne",     "eta_min": 22},
    {"zip": "46807", "zone_name": "Waynedale",      "eta_min": 28},
    {"zip": "46809", "zone_name": "Waynedale",      "eta_min": 30},
    {"zip": "46804", "zone_name": "Aboite",         "eta_min": 25},
    {"zip": "46814", "zone_name": "Aboite",         "eta_min": 27},
    {"zip": "46818", "zone_name": "Huntertown",     "eta_min": 30},
    {"zip": "46765", "zone_name": "Leo-Cedarville", "eta_min": 32},
    {"zip": "46815", "zone_name": "New Haven",      "eta_min": 26},
]


async def seed_coverage_zips(db: AsyncSession) -> None:
    """Idempotent upsert keyed on the ZIP (PK)."""
    seeded = 0
    for entry in _COVERAGE_ZIPS:
        existing = await db.execute(
            select(CoverageZip).where(CoverageZip.zip == entry["zip"])
        )
        if existing.scalar_one_or_none():
            continue
        db.add(CoverageZip(**entry))
        seeded += 1
    await db.commit()
    logger.info("Coverage ZIPs seed complete — %d new ZIP(s) inserted.", seeded)
