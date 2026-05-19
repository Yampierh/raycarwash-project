"""
tests/test_public_endpoints.py — Plan 19 Track 1 read endpoints.

Covers the 5 endpoints wired in this commit:
    GET  /api/v1/public/testimonials
    GET  /api/v1/public/faq
    GET  /api/v1/public/coverage-zones
    POST /api/v1/public/coverage/check
    GET  /api/v1/public/waitlist/count

The remaining 4 (stats, detailer-benchmarks, contact, waitlist/join)
still return 501 and have their own tests in the follow-up commit.

Tests use the canonical `client` fixture from conftest.py — empty DB,
rate limiter disabled, Redis mocked. Each suite that needs data calls
the corresponding `seed_public` function explicitly so the assertions
are tied to known fixture counts (11 testimonials, 31 FAQs, etc.).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.db.seed_public import (
    seed_coverage_zips,
    seed_coverage_zones,
    seed_faq,
    seed_testimonials,
)


# ─── Testimonials ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_testimonials_returns_empty_when_unseeded(client: AsyncClient):
    """Default: no rows → empty array, NOT 404. The endpoint is a list,
    not a "find one" — empty is a valid state."""
    r = await client.get("/api/v1/public/testimonials")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["testimonials"] == []
    # Cache-Control header per Plan 19 §10.2
    assert "public" in r.headers.get("cache-control", "").lower()
    assert "max-age=3600" in r.headers["cache-control"]


@pytest.mark.asyncio
async def test_testimonials_returns_seeded_data(client_with_db):
    """After seeding: returns the 11 rows we inserted. Default limit=10,
    so only 10 are returned and the rest hide behind the `limit` knob."""
    ac, db_session = client_with_db
    await seed_testimonials(db_session)

    r = await ac.get("/api/v1/public/testimonials")
    assert r.status_code == 200
    items = r.json()["data"]["testimonials"]
    # Default limit is 10
    assert len(items) == 10
    # Sorted by sort_order — first item is featured Maria G. (sort_order=10)
    first = items[0]
    assert first["name"] == "Maria G."
    assert first["rating"] == 5
    assert first["featured"] is True


@pytest.mark.asyncio
async def test_testimonials_filter_by_role(client_with_db):
    ac, db_session = client_with_db
    await seed_testimonials(db_session)

    # Detailer role → only the 3 detailer quotes
    r = await ac.get("/api/v1/public/testimonials?role=detailer")
    items = r.json()["data"]["testimonials"]
    assert len(items) == 3
    assert {i["name"] for i in items} == {"Marcus T.", "Trey W.", "Jamal R."}
    assert all(i["role"] == "detailer" for i in items)


@pytest.mark.asyncio
async def test_testimonials_filter_featured_and_limit(client_with_db):
    ac, db_session = client_with_db
    await seed_testimonials(db_session)

    # Landing block: client + featured + limit=4
    r = await ac.get("/api/v1/public/testimonials?role=client&featured=true&limit=4")
    items = r.json()["data"]["testimonials"]
    assert len(items) == 4
    assert all(i["featured"] is True for i in items)
    assert all(i["role"] == "client" for i in items)
    # Sort order: Maria, Derrick, Jonas, Anna
    assert [i["name"] for i in items] == [
        "Maria G.", "Derrick P.", "Jonas R.", "Anna L.",
    ]


@pytest.mark.asyncio
async def test_testimonials_limit_validation(client: AsyncClient):
    """Pydantic Query bounds: 1 ≤ limit ≤ 50."""
    r = await client.get("/api/v1/public/testimonials?limit=0")
    assert r.status_code == 422
    r = await client.get("/api/v1/public/testimonials?limit=51")
    assert r.status_code == 422


# ─── FAQ ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_faq_returns_seeded_data(client_with_db):
    ac, db_session = client_with_db
    await seed_faq(db_session)

    r = await ac.get("/api/v1/public/faq")
    assert r.status_code == 200
    items = r.json()["data"]["faq"]
    # 13 rider + 7 detailer + 6 mechanic + 5 provider = 31
    assert len(items) == 31
    assert "max-age=3600" in r.headers["cache-control"]


@pytest.mark.asyncio
async def test_faq_filter_by_category(client_with_db):
    ac, db_session = client_with_db
    await seed_faq(db_session)

    for category, expected in [
        ("rider", 13),
        ("detailer", 7),
        ("mechanic", 6),
        ("provider", 5),
    ]:
        r = await ac.get(f"/api/v1/public/faq?category={category}")
        items = r.json()["data"]["faq"]
        assert len(items) == expected, f"{category}: got {len(items)}, want {expected}"
        assert all(i["category"] == category for i in items)


@pytest.mark.asyncio
async def test_faq_invalid_category_returns_422(client: AsyncClient):
    """FastAPI Literal enforces enum membership at the query layer."""
    r = await client.get("/api/v1/public/faq?category=invalid")
    assert r.status_code == 422


# ─── Coverage zones ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_coverage_zones_returns_seeded_data(client_with_db):
    ac, db_session = client_with_db
    await seed_coverage_zones(db_session)

    r = await ac.get("/api/v1/public/coverage-zones")
    assert r.status_code == 200
    zones = r.json()["data"]["zones"]
    assert len(zones) == 6
    assert "max-age=86400" in r.headers["cache-control"]

    # Primary zone is Fort Wayne with SVG (50, 50, 12)
    primary = next(z for z in zones if z["is_primary"])
    assert primary["name"] == "Fort Wayne"
    assert primary["svg"] == {"cx": 50, "cy": 50, "r": 12}

    # Non-primary names match the prototype
    non_primary_names = {z["name"] for z in zones if not z["is_primary"]}
    assert non_primary_names == {
        "Aboite", "Huntertown", "Leo-Cedarville", "New Haven", "Waynedale",
    }


# ─── Coverage check ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_coverage_check_known_zip(client_with_db):
    ac, db_session = client_with_db
    await seed_coverage_zips(db_session)

    r = await ac.post("/api/v1/public/coverage/check", json={"zip": "46802"})
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["covered"] is True
    assert body["zone"] == "Fort Wayne"
    # eta_at_launch is the human label "~22 min" (eta_min=22 in seed)
    assert body["eta_at_launch"] == "~22 min"
    # POST responses aren't cached by default (RFC 7234 §3); the
    # Cache-Control header is intentionally not set on this endpoint.


@pytest.mark.asyncio
async def test_coverage_check_unknown_zip(client_with_db):
    ac, db_session = client_with_db
    await seed_coverage_zips(db_session)

    r = await ac.post("/api/v1/public/coverage/check", json={"zip": "99999"})
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["covered"] is False
    assert body["zone"] is None
    assert body["eta_at_launch"] is None


@pytest.mark.asyncio
async def test_coverage_check_invalid_zip_format_returns_422(client: AsyncClient):
    """5-digit numeric regex per Plan 19 §10.4."""
    for bad in ["4680", "468022", "4680A", "abc12"]:
        r = await client.post("/api/v1/public/coverage/check", json={"zip": bad})
        assert r.status_code == 422, f"ZIP {bad!r} should 422, got {r.status_code}"


# ─── Waitlist count ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_waitlist_count_empty(client: AsyncClient):
    """No signups yet → count=0, but the wait-time string still shows
    a positive minimum (`max(1, ...)` in the service)."""
    r = await client.get("/api/v1/public/waitlist/count")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["count"] == 0
    assert body["avg_wait_weeks"] == "1 weeks"
    # Plan 19 §10.2 — 30s edge cache for the live counter
    assert "max-age=30" in r.headers["cache-control"]


@pytest.mark.asyncio
async def test_waitlist_count_with_entries(client_with_db):
    """Insert 5 waitlist entries; count should reflect them and the
    wait-time label rounds up by the 80-per-week service constant."""
    ac, db_session = client_with_db
    from domains.public.models import WaitlistEntry, WaitlistRole

    for i in range(5):
        db_session.add(WaitlistEntry(
            email=f"signup{i}@example.com",
            role=WaitlistRole.MECHANIC,
            position=i + 1,
        ))
    await db_session.commit()

    r = await ac.get("/api/v1/public/waitlist/count")
    body = r.json()["data"]
    assert body["count"] == 5
    # 5 / 80 → ceil() → 1 week
    assert body["avg_wait_weeks"] == "1 weeks"


# ─── Contact form (POST /contact) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_contact_happy_path(client: AsyncClient):
    """Successful submission returns 201 + envelope with new id."""
    r = await client.post(
        "/api/v1/public/contact",
        json={
            "name": "Alex Reyes",
            "email": "alex@example.com",
            "subject": "Question about coverage",
            "message": "Do you serve 46765?",
        },
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["status"] == "received"
    # id is a UUID — at least 36 chars with hyphens
    assert len(data["id"]) == 36 and data["id"].count("-") == 4


@pytest.mark.asyncio
async def test_contact_email_is_lowercased(client_with_db):
    """Email normalisation happens in the Pydantic validator —
    UPPERCASE input must be stored as lowercase."""
    ac, db_session = client_with_db
    from sqlalchemy import select
    from domains.public.models import ContactSubmission

    r = await ac.post(
        "/api/v1/public/contact",
        json={
            "name": "Casey",
            "email": "CASEY@EXAMPLE.COM",
            "message": "hi",
        },
    )
    assert r.status_code == 201
    rows = (await db_session.execute(select(ContactSubmission))).scalars().all()
    assert len(rows) == 1
    assert rows[0].email == "casey@example.com"


@pytest.mark.asyncio
async def test_contact_validation_errors(client: AsyncClient):
    """Pydantic field constraints fire 422."""
    bad_payloads = [
        {"email": "x@y.com", "message": "hi"},                  # name missing
        {"name": "X", "message": "hi"},                          # email missing
        {"name": "X", "email": "x@y.com"},                       # message missing
        {"name": "X", "email": "not-an-email", "message": "hi"}, # bad email
        {"name": "X", "email": "x@y.com", "message": "y" * 5001}, # message too long
    ]
    for payload in bad_payloads:
        r = await client.post("/api/v1/public/contact", json=payload)
        assert r.status_code == 422, f"payload {payload!r} should 422, got {r.status_code}"


@pytest.mark.asyncio
async def test_contact_20_per_day_per_email_cap(client_with_db):
    """The slowapi 3/min/IP cap is bypassed in tests (rate limiter
    disabled). The per-email/day cap is service-layer logic that fires
    even without slowapi — verifies it returns 429 with the
    rate_limit_exceeded code from BusinessError."""
    ac, db_session = client_with_db
    from datetime import datetime, timezone
    from domains.public.models import ContactSubmission

    email = "spammy@example.com"
    # Seed 20 prior submissions today
    now = datetime.now(timezone.utc)
    for i in range(20):
        db_session.add(ContactSubmission(
            name=f"S {i}",
            email=email,
            message="prior",
            created_at=now,
        ))
    await db_session.commit()

    r = await ac.post(
        "/api/v1/public/contact",
        json={"name": "S", "email": email, "message": "one more"},
    )
    assert r.status_code == 429
    body = r.json()
    assert body["error"]["code"] == "rate_limit_exceeded"


# ─── Waitlist join (POST /waitlist/join) ───────────────────────────────


@pytest.mark.asyncio
async def test_waitlist_join_happy_path(client: AsyncClient):
    r = await client.post(
        "/api/v1/public/waitlist/join",
        json={"email": "first@example.com", "role": "mechanic"},
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert len(data["id"]) == 36
    assert data["position"] == 1


@pytest.mark.asyncio
async def test_waitlist_join_role_defaults_to_mechanic(client_with_db):
    """`role` is optional in the schema; default = WaitlistRole.MECHANIC."""
    ac, db_session = client_with_db
    from sqlalchemy import select
    from domains.public.models import WaitlistEntry

    r = await ac.post(
        "/api/v1/public/waitlist/join",
        json={"email": "default-role@example.com"},
    )
    assert r.status_code == 201

    row = (await db_session.execute(select(WaitlistEntry))).scalar_one()
    assert row.role.value == "mechanic"


@pytest.mark.asyncio
async def test_waitlist_join_duplicate_returns_409(client: AsyncClient):
    """Two signups with the same email — second one must 409."""
    payload = {"email": "dup@example.com", "role": "mechanic"}
    r1 = await client.post("/api/v1/public/waitlist/join", json=payload)
    r2 = await client.post("/api/v1/public/waitlist/join", json=payload)

    assert r1.status_code == 201
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "email_already_on_waitlist"


@pytest.mark.asyncio
async def test_waitlist_join_position_increments(client_with_db):
    """Position is the row's index at insert time. With empty seed
    (no rows pre-existing), positions go 1, 2, 3, ..."""
    ac, _ = client_with_db
    positions = []
    for i in range(3):
        r = await ac.post(
            "/api/v1/public/waitlist/join",
            json={"email": f"pos{i}@example.com", "role": "mechanic"},
        )
        assert r.status_code == 201
        positions.append(r.json()["data"]["position"])
    assert positions == [1, 2, 3]


@pytest.mark.asyncio
async def test_waitlist_join_email_normalised(client_with_db):
    """Email is lowercased server-side, so MIXED-case retries hit the
    UNIQUE constraint just like exact-case ones."""
    ac, db_session = client_with_db
    from sqlalchemy import select
    from domains.public.models import WaitlistEntry

    r1 = await ac.post(
        "/api/v1/public/waitlist/join",
        json={"email": "MixedCase@Example.COM", "role": "mechanic"},
    )
    assert r1.status_code == 201

    # Stored lowercase
    row = (await db_session.execute(select(WaitlistEntry))).scalar_one()
    assert row.email == "mixedcase@example.com"

    # Second submission with different casing still collides
    r2 = await ac.post(
        "/api/v1/public/waitlist/join",
        json={"email": "mixedcase@example.com", "role": "mechanic"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_waitlist_join_invalid_role_returns_422(client: AsyncClient):
    """Pydantic enum validation rejects unknown roles."""
    r = await client.post(
        "/api/v1/public/waitlist/join",
        json={"email": "x@example.com", "role": "manager"},
    )
    assert r.status_code == 422


# ─── Stats (GET /stats) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stats_returns_zeros_on_fresh_db(client: AsyncClient):
    """Fresh DB: no appointments, no reviews, no active detailers →
    every count is 0 and the labels still render (zero is shown as
    "0", not "0+"; the "+" suffix only kicks in at ≥100)."""
    r = await client.get("/api/v1/public/stats")
    assert r.status_code == 200
    data = r.json()["data"]

    assert data["deliveries"] == 0
    assert data["deliveries_label"] == "0"
    assert data["active_detailers"] == 0
    assert data["total_reviews"] == 0
    # avg_rating COALESCE'd to 0.0 on empty reviews
    assert data["avg_rating"] == 0.0
    assert data["avg_rating_label"] == "0.0★"

    # Static placeholders (Plan 19 §5 — marketing-approved approximations)
    assert data["avg_eta_min"] == 22
    assert data["median_earnings_per_hr"] == 42

    # Plan 19 §10.2 — 1h CDN cache
    assert "max-age=3600" in r.headers["cache-control"]


@pytest.mark.asyncio
async def test_stats_aggregates_from_db(client_with_db):
    """Seeded data: completed appointments, reviews, an active provider →
    the response reflects the real counts and avg_rating."""
    ac, db_session = client_with_db
    from datetime import datetime, timezone

    from sqlalchemy import select
    from domains.appointments.models import Appointment, AppointmentStatus
    from domains.auth.models import Role, UserRoleAssociation
    from domains.providers.models import ProviderProfile
    from domains.reviews.models import Review
    from domains.services_catalog.models import Service
    from domains.users.models import ClientProfile, OnboardingStatus, User

    # Need an active detailer + a client + a service for FKs
    detailer_role = (await db_session.execute(
        select(Role).where(Role.name == "detailer")
    )).scalar_one()
    client_role = (await db_session.execute(
        select(Role).where(Role.name == "client")
    )).scalar_one()
    service = (await db_session.execute(
        select(Service).limit(1)
    )).scalar_one()

    detailer = User(
        email="stats-d@example.com",
        full_name="Stats Detailer",
        password_hash="x",
        is_active=True,
        onboarding_status=OnboardingStatus.COMPLETED,
    )
    customer = User(
        email="stats-c@example.com",
        full_name="Stats Customer",
        password_hash="x",
        is_active=True,
        onboarding_status=OnboardingStatus.COMPLETED,
    )
    db_session.add_all([detailer, customer])
    await db_session.flush()
    db_session.add_all([
        UserRoleAssociation(user_id=detailer.id, role_id=detailer_role.id),
        UserRoleAssociation(user_id=customer.id, role_id=client_role.id),
        ProviderProfile(
            user_id=detailer.id,
            bio="bio",
            years_of_experience=3,
            service_radius_miles=25,
            timezone="America/Indiana/Indianapolis",
            is_accepting_bookings=True,
        ),
        ClientProfile(user_id=customer.id),
    ])

    # Two completed appointments + one in_progress (only completed count).
    # Reviews go 5★ on the first, 3★ on the second; in_progress has no
    # review (would violate UNIQUE(appointment_id) + business rule).
    completed_appts: list[Appointment] = []
    for status in (
        AppointmentStatus.COMPLETED,
        AppointmentStatus.COMPLETED,
        AppointmentStatus.IN_PROGRESS,
    ):
        appt = Appointment(
            client_id=customer.id,
            detailer_id=detailer.id,
            service_id=service.id,
            scheduled_time=datetime(2026, 5, 19, tzinfo=timezone.utc),
            estimated_price=10_000,
            status=status,
        )
        db_session.add(appt)
        await db_session.flush()
        if status == AppointmentStatus.COMPLETED:
            completed_appts.append(appt)

    for appt, rating in zip(completed_appts, [5, 3]):
        db_session.add(Review(
            appointment_id=appt.id,
            reviewer_id=customer.id,
            detailer_id=detailer.id,
            rating=rating,
        ))

    await db_session.commit()

    r = await ac.get("/api/v1/public/stats")
    data = r.json()["data"]

    # 2 completed appointments → deliveries=2 (label "2", <100 threshold)
    assert data["deliveries"] == 2
    assert data["deliveries_label"] == "2"
    # 1 active provider
    assert data["active_detailers"] == 1
    # 2 reviews (5★ + 3★ → avg 4.0)
    assert data["total_reviews"] == 2
    assert data["avg_rating"] == 4.0
    assert data["avg_rating_label"] == "4.0★"


@pytest.mark.asyncio
async def test_stats_label_rounding(client: AsyncClient):
    """`_format_round_with_plus` rules — unit-test through the API.
    We can't easily insert 100+ appointments here, so we directly
    test the helper."""
    from domains.public.service import _format_round_with_plus

    assert _format_round_with_plus(0) == "0"
    assert _format_round_with_plus(47) == "47"
    assert _format_round_with_plus(100) == "100+"
    assert _format_round_with_plus(437) == "400+"
    assert _format_round_with_plus(2_437) == "2,400+"
    assert _format_round_with_plus(15_999) == "15,900+"


# ─── Detailer benchmarks (GET /stats/detailer-benchmarks) ──────────────


@pytest.mark.asyncio
async def test_detailer_benchmarks_returns_static_marketing_values(client: AsyncClient):
    """Static config — no DB dependency. Verifies the cents convention
    holds (e.g. median_weekly=184_000 == $1,840) and the labels match
    the prototype copy."""
    r = await client.get("/api/v1/public/stats/detailer-benchmarks")
    assert r.status_code == 200
    data = r.json()["data"]

    # Cents convention
    assert data["median_weekly"] == 184_000
    assert data["top_quartile_weekly"] == 272_000
    assert data["top_10pct_weekly"] == 340_000
    assert data["avg_per_job"] == 11_200

    # Pre-formatted labels for display
    assert data["median_weekly_label"] == "$1,840 / wk"
    assert data["top_quartile_weekly_label"] == "$2,720 / wk"
    assert data["top_10pct_weekly_label"] == "$3,400+ / wk"
    assert data["avg_per_job_label"] == "$112"

    # Plan 19 §10.2 — 24h CDN cache
    cc = r.headers.get("cache-control", "")
    assert "max-age=86400" in cc
