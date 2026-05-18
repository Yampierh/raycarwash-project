"""
tests/test_users_client_preferences.py — Phase 4 chunk V
(/api/v1/users/me/client-preferences).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str) -> str:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201
    onboarding = reg.json()["onboarding_token"]
    phone_suffix = str(abs(hash(email)) % 10_000_000).zfill(7)
    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Pref Tester", "phone_number": f"+155{phone_suffix}"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Secure1234!"},
    )
    return login.json()["access_token"]


async def _create_vehicle(client: AsyncClient, token: str) -> str:
    resp = await client.post(
        "/api/v1/vehicles",
        json={
            "make": "Honda", "model": "Civic", "year": 2021,
            "color": "white",
            "license_plate": f"P{uuid.uuid4().hex[:6].upper()}",
            "body_class": "Sedan",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


async def _create_address(client: AsyncClient, token: str) -> str:
    """Create an address with the geocoding adapter stubbed at the
    service module level (Nominatim is rate-limited and would flake)."""
    from unittest.mock import AsyncMock
    from domains.users import address_service as svc
    from infrastructure.geocoding.base import GeocodeResult

    fake = AsyncMock()
    fake.geocode = AsyncMock(return_value=GeocodeResult(
        latitude=39.0, longitude=-86.0,
        formatted_address="Stub St, Indianapolis, IN",
        confidence=0.9,
    ))
    # Use a context-managed monkeypatch via direct setattr; un-set after.
    saved = svc.get_geocoding_adapter
    svc.get_geocoding_adapter = lambda: fake
    try:
        resp = await client.post(
            "/api/v1/users/me/addresses",
            json={
                "label": "Home",
                "line1": "1 Test St",
                "city": "Indianapolis", "state": "IN",
                "zip_code": "46201", "country": "US",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        svc.get_geocoding_adapter = saved
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


# ─── GET defaults ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_preferences_returns_defaults_for_new_user(
    client: AsyncClient,
) -> None:
    token = await _login(client, "prefs-new@test.com")
    resp = await client.get(
        "/api/v1/users/me/client-preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["default_vehicle_id"] is None
    assert data["default_address_id"] is None
    assert data["marketing_opt_in"] is False
    assert data["frequency_preference"] is None


# ─── PUT updates with FK ownership validation ─────────────────────────────────


@pytest.mark.asyncio
async def test_put_preferences_updates_all_fields(
    client: AsyncClient,
) -> None:
    token = await _login(client, "prefs-set@test.com")
    veh_id = await _create_vehicle(client, token)
    addr_id = await _create_address(client, token)

    resp = await client.put(
        "/api/v1/users/me/client-preferences",
        json={
            "default_vehicle_id": veh_id,
            "default_address_id": addr_id,
            "marketing_opt_in": True,
            "frequency_preference": "monthly",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["default_vehicle_id"] == veh_id
    assert data["default_address_id"] == addr_id
    assert data["marketing_opt_in"] is True
    assert data["frequency_preference"] == "monthly"


@pytest.mark.asyncio
async def test_put_preferences_clears_with_null(
    client: AsyncClient,
) -> None:
    token = await _login(client, "prefs-clear@test.com")
    veh_id = await _create_vehicle(client, token)

    # First set, then clear.
    await client.put(
        "/api/v1/users/me/client-preferences",
        json={
            "default_vehicle_id": veh_id,
            "default_address_id": None,
            "marketing_opt_in": True,
            "frequency_preference": "weekly",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.put(
        "/api/v1/users/me/client-preferences",
        json={
            "default_vehicle_id": None,
            "default_address_id": None,
            "marketing_opt_in": False,
            "frequency_preference": None,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["default_vehicle_id"] is None
    assert data["frequency_preference"] is None


@pytest.mark.asyncio
async def test_put_preferences_rejects_unowned_vehicle(
    client: AsyncClient,
) -> None:
    """default_vehicle_id pointing at someone else's vehicle (or a
    bogus UUID) must 404, NOT silently accept and write a dangling
    reference."""
    token = await _login(client, "prefs-cross@test.com")
    bogus_veh = uuid.uuid4()
    resp = await client.put(
        "/api/v1/users/me/client-preferences",
        json={
            "default_vehicle_id": str(bogus_veh),
            "default_address_id": None,
            "marketing_opt_in": False,
            "frequency_preference": None,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_preferences_rejects_unowned_address(
    client: AsyncClient,
) -> None:
    token = await _login(client, "prefs-crossaddr@test.com")
    bogus_addr = uuid.uuid4()
    resp = await client.put(
        "/api/v1/users/me/client-preferences",
        json={
            "default_vehicle_id": None,
            "default_address_id": str(bogus_addr),
            "marketing_opt_in": False,
            "frequency_preference": None,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ─── Hub preferences block reflects the PUT ──────────────────────────────────


@pytest.mark.asyncio
async def test_hub_preferences_block_reflects_put(
    client: AsyncClient,
) -> None:
    token = await _login(client, "prefs-hub@test.com")
    veh_id = await _create_vehicle(client, token)
    await client.put(
        "/api/v1/users/me/client-preferences",
        json={
            "default_vehicle_id": veh_id,
            "default_address_id": None,
            "marketing_opt_in": True,
            "frequency_preference": "monthly",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/users/me?include=preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    prefs = resp.json()["data"]["preferences"]
    assert prefs["default_vehicle_id"] == veh_id
    assert prefs["marketing_opt_in"] is True
    assert prefs["frequency_preference"] == "monthly"
