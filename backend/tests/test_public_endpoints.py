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
