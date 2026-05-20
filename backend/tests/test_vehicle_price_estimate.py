"""
tests/test_vehicle_price_estimate.py — Plan 24 §3 C-1.

Anonymous price-preview endpoint for the customer-signup vehicle step.

Verifies:
  - Mid-size SUV (Honda Pilot) → estimated_size="medium"
  - Sedan (Toyota Camry) → "small"
  - Pickup (Ford F-150) → "large"
  - Van (Chrysler Pacifica) → "xl"
  - Unknown model → "small" (safe fall-through)
  - Returns at least 1 tier from each anchor category
  - Cache-Control header set per Plan 19 §10.2 (1h cache)
  - Year bounds (1970..2030) enforced by Pydantic Query

Endpoint is anonymous — no Authorization header required.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_price_estimate_mid_size_suv(client: AsyncClient):
    r = await client.get(
        "/api/v1/vehicles/price-estimate",
        params={"year": 2022, "make": "Honda", "model": "Pilot"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["estimated_size"] == "medium"
    assert "SUV" in data["size_label"]
    assert data["year"] == 2022
    assert data["make"] == "Honda"
    assert data["model"] == "Pilot"
    # Anchor tiers populated from the seed catalog (basic_wash + full_detail)
    categories = {t["category"] for t in data["tiers"]}
    assert "basic_wash" in categories
    assert "full_detail" in categories
    # Prices are positive integer cents
    for tier in data["tiers"]:
        assert isinstance(tier["price_cents"], int)
        assert tier["price_cents"] > 0
        assert tier["duration_minutes"] > 0
    # Plan 19 §10.2 — 1h CDN cache
    assert "max-age=3600" in r.headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_price_estimate_sedan_is_small(client: AsyncClient):
    r = await client.get(
        "/api/v1/vehicles/price-estimate",
        params={"year": 2024, "make": "Toyota", "model": "Camry"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["estimated_size"] == "small"


@pytest.mark.asyncio
async def test_price_estimate_tesla_model3_is_small(client: AsyncClient):
    """Tesla Model 3 — keyword doesn't match the MEDIUM list (only
    "model y"/"model x" do), so it falls through to SMALL like other
    sedans."""
    r = await client.get(
        "/api/v1/vehicles/price-estimate",
        params={"year": 2023, "make": "Tesla", "model": "Model 3"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["estimated_size"] == "small"


@pytest.mark.asyncio
async def test_price_estimate_pickup_is_large(client: AsyncClient):
    r = await client.get(
        "/api/v1/vehicles/price-estimate",
        params={"year": 2023, "make": "Ford", "model": "F-150"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["estimated_size"] == "large"
    assert "Pickup" in data["size_label"]


@pytest.mark.asyncio
async def test_price_estimate_van_is_xl(client: AsyncClient):
    r = await client.get(
        "/api/v1/vehicles/price-estimate",
        params={"year": 2022, "make": "Chrysler", "model": "Pacifica"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["estimated_size"] == "xl"
    assert "Van" in data["size_label"]


@pytest.mark.asyncio
async def test_price_estimate_unknown_model_falls_back_to_small(client: AsyncClient):
    """Safe default — under-quoting beats over-quoting at signup."""
    r = await client.get(
        "/api/v1/vehicles/price-estimate",
        params={"year": 2024, "make": "Nokia", "model": "Hyperloop-9000"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["estimated_size"] == "small"


@pytest.mark.asyncio
async def test_price_estimate_price_scales_with_size(client: AsyncClient):
    """Larger vehicles cost more — SMALL < MEDIUM < LARGE < XL for the
    same service. Sanity check against the seed multipliers in seed.py."""
    sizes = []
    for params in [
        {"year": 2024, "make": "Toyota", "model": "Camry"},      # small
        {"year": 2024, "make": "Honda",  "model": "Pilot"},      # medium
        {"year": 2024, "make": "Ford",   "model": "F-150"},      # large
        {"year": 2024, "make": "Honda",  "model": "Odyssey"},    # xl
    ]:
        r = await client.get("/api/v1/vehicles/price-estimate", params=params)
        data = r.json()["data"]
        basic = next(t for t in data["tiers"] if t["category"] == "basic_wash")
        sizes.append(basic["price_cents"])
    assert sizes[0] < sizes[1] < sizes[2] < sizes[3]


@pytest.mark.asyncio
async def test_price_estimate_year_bounds(client: AsyncClient):
    """Pydantic Query enforces 1970..2030."""
    for year in (1969, 2031, 0):
        r = await client.get(
            "/api/v1/vehicles/price-estimate",
            params={"year": year, "make": "Honda", "model": "Pilot"},
        )
        assert r.status_code == 422, f"year={year} should 422"


@pytest.mark.asyncio
async def test_price_estimate_is_anonymous(client: AsyncClient):
    """No Authorization header → still 200. C-1 fires during signup
    before the user has an account."""
    r = await client.get(
        "/api/v1/vehicles/price-estimate",
        params={"year": 2024, "make": "Honda", "model": "Civic"},
    )
    assert r.status_code == 200
