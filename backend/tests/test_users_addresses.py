"""
tests/test_users_addresses.py — Phase 4 chunk T.

Covers the CRUD surface for /api/v1/users/me/addresses + the addresses
block in the Profile Hub.

Geocoding is stubbed via dependency override so tests don't hit
Nominatim (rate-limited 1 req/s, would flake).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dependencies as deps
from domains.users.user_address import UserAddress
from infrastructure.geocoding.base import GeocodeResult


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str = "addr@test.com") -> str:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201, reg.text
    onboarding = reg.json()["onboarding_token"]
    # Derive a unique phone per email — phone_hash has a unique index so a
    # hard-coded number would collide on the second registration in the
    # same test.
    phone_suffix = str(abs(hash(email)) % 10_000_000).zfill(7)
    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Addr Tester", "phone_number": f"+155{phone_suffix}"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Secure1234!"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


@pytest.fixture
def stub_geocoder(monkeypatch):
    """Replace the geocoding adapter with one that returns a fixed point.

    address_service.py does `from app.core.dependencies import
    get_geocoding_adapter`, so the active symbol is
    `address_service.get_geocoding_adapter`. We patch THAT — patching
    deps.get_geocoding_adapter would leave the service's already-bound
    reference intact and the real Nominatim call would still fire.
    """
    from domains.users import address_service as svc

    fake = AsyncMock()
    fake.geocode = AsyncMock(
        return_value=GeocodeResult(
            latitude=39.7684,
            longitude=-86.1581,
            formatted_address="Stubbed, Indianapolis, IN",
            confidence=0.9,
        )
    )
    monkeypatch.setattr(svc, "get_geocoding_adapter", lambda: fake)
    return fake


def _addr_payload(**overrides):
    base = {
        "label": "Home",
        "line1": "123 Test St",
        "city": "Indianapolis",
        "state": "IN",
        "zip_code": "46201",
        "country": "US",
    }
    base.update(overrides)
    return base


# ─── Create ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_first_address_becomes_default_even_when_not_requested(
    client: AsyncClient, stub_geocoder,
) -> None:
    token = await _login(client, "addr-first@test.com")
    resp = await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(is_default=False),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["is_default"] is True, "first address must auto-default"
    # Pydantic serializes Decimal as a string with provider precision —
    # don't pin the exact format, just assert it round-trips numerically.
    assert float(data["latitude"]) == pytest.approx(39.7684, abs=1e-4)
    assert float(data["longitude"]) == pytest.approx(-86.1581, abs=1e-4)
    assert data["h3_index_r9"] is not None


@pytest.mark.asyncio
async def test_create_persists_with_null_coords_on_geocoding_error(
    client: AsyncClient, monkeypatch,
) -> None:
    """Plan §10.4.4 — geocoding failures must NOT block the user from
    saving the address. The matching engine just skips coord-less rows."""
    from infrastructure.geocoding.base import GeocodingError
    from domains.users import address_service as svc

    failing = AsyncMock()
    failing.geocode = AsyncMock(side_effect=GeocodingError("nominatim 503"))
    monkeypatch.setattr(svc, "get_geocoding_adapter", lambda: failing)

    token = await _login(client, "addr-nogeo@test.com")
    resp = await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["latitude"] is None
    assert data["longitude"] is None
    assert data["h3_index_r9"] is None


# ─── Default flipping ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_setting_default_is_atomic_only_one_default_remains(
    client: AsyncClient, stub_geocoder, db_session: AsyncSession,
) -> None:
    token = await _login(client, "addr-default@test.com")
    first = await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(label="Home"),
        headers={"Authorization": f"Bearer {token}"},
    )
    second = await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(label="Work", line1="200 Office Pkwy"),
        headers={"Authorization": f"Bearer {token}"},
    )
    second_id = second.json()["data"]["id"]

    resp = await client.patch(
        f"/api/v1/users/me/addresses/{second_id}/default",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["is_default"] is True

    # Verify partial unique invariant: exactly one is_default per user.
    rows = (await db_session.scalars(
        select(UserAddress).where(
            UserAddress.is_default.is_(True),
            UserAddress.is_deleted.is_(False),
        )
    )).all()
    assert len(rows) == 1
    assert str(rows[0].id) == second_id


@pytest.mark.asyncio
async def test_set_default_on_unknown_id_returns_404(
    client: AsyncClient, stub_geocoder,
) -> None:
    token = await _login(client, "addr-404default@test.com")
    bogus = uuid.uuid4()
    resp = await client.patch(
        f"/api/v1/users/me/addresses/{bogus}/default",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404, resp.text


# ─── Update ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_label_only_does_not_regeocode(
    client: AsyncClient, stub_geocoder,
) -> None:
    """If the user just renames "Home" → "House", we must not waste a
    call on the rate-limited geocoder."""
    token = await _login(client, "addr-rename@test.com")
    create = await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    addr_id = create.json()["data"]["id"]
    initial_calls = stub_geocoder.geocode.await_count

    resp = await client.patch(
        f"/api/v1/users/me/addresses/{addr_id}",
        json={"label": "House"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["label"] == "House"
    assert stub_geocoder.geocode.await_count == initial_calls, (
        "label-only change must not trigger re-geocoding"
    )


@pytest.mark.asyncio
async def test_update_city_triggers_regeocode(
    client: AsyncClient, stub_geocoder,
) -> None:
    token = await _login(client, "addr-move@test.com")
    create = await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    addr_id = create.json()["data"]["id"]
    initial_calls = stub_geocoder.geocode.await_count

    resp = await client.patch(
        f"/api/v1/users/me/addresses/{addr_id}",
        json={"city": "Carmel", "zip_code": "46032"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert stub_geocoder.geocode.await_count == initial_calls + 1


# ─── Delete + auto-promote ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deleting_default_promotes_next_address(
    client: AsyncClient, stub_geocoder, db_session: AsyncSession,
) -> None:
    token = await _login(client, "addr-promote@test.com")
    first = await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(label="Home"),
        headers={"Authorization": f"Bearer {token}"},
    )
    second = await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(label="Work", line1="200 Office Pkwy"),
        headers={"Authorization": f"Bearer {token}"},
    )
    first_id = first.json()["data"]["id"]
    second_id = second.json()["data"]["id"]

    # `first` is the auto-default. Delete it.
    delete = await client.delete(
        f"/api/v1/users/me/addresses/{first_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete.status_code == 204, delete.text

    # `second` should be the new default.
    listing = await client.get(
        "/api/v1/users/me/addresses",
        headers={"Authorization": f"Bearer {token}"},
    )
    items = listing.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == second_id
    assert items[0]["is_default"] is True


@pytest.mark.asyncio
async def test_cannot_read_another_users_address(
    client: AsyncClient, stub_geocoder,
) -> None:
    alice_token = await _login(client, "alice@test.com")
    bob_token = await _login(client, "bob@test.com")

    create = await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    alice_addr_id = create.json()["data"]["id"]

    resp = await client.get(
        f"/api/v1/users/me/addresses/{alice_addr_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert resp.status_code == 404, "cross-user access must 404, never leak"


# ─── Profile Hub integration ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hub_addresses_block_includes_created_address(
    client: AsyncClient, stub_geocoder,
) -> None:
    token = await _login(client, "addr-hub@test.com")
    await client.post(
        "/api/v1/users/me/addresses",
        json=_addr_payload(label="Home"),
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/users/me?include=addresses",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    addrs = body["data"]["addresses"]
    assert len(addrs) == 1
    assert addrs[0]["label"] == "Home"
    assert addrs[0]["is_default"] is True
    assert "addresses" in (body["meta"].get("includes") or [])


# ── Plan 24 §3 C-3 — opt-in coverage gate ──────────────────────────────


@pytest.mark.asyncio
async def test_address_coverage_check_accepts_seeded_zip(
    client: AsyncClient, stub_geocoder, db_session: AsyncSession,
) -> None:
    """ZIP 46802 is in the launch market (Fort Wayne). The signup flow
    sends `enforce_coverage_check=True` and expects 201."""
    from app.db.seed_public import seed_coverage_zips

    await seed_coverage_zips(db_session)
    token = await _login(client, "addr-cov-ok@test.com")

    resp = await client.post(
        "/api/v1/users/me/addresses",
        json={
            "label": "Home",
            "line1": "123 Elm St",
            "city": "Fort Wayne",
            "state": "IN",
            "zip_code": "46802",
            "enforce_coverage_check": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["zip_code"] == "46802"


@pytest.mark.asyncio
async def test_address_coverage_check_rejects_out_of_area_zip(
    client: AsyncClient, stub_geocoder, db_session: AsyncSession,
) -> None:
    """ZIP 10001 (NYC) is outside the launch market. enforce_coverage_check
    rejects with 422 zip_outside_coverage."""
    from app.db.seed_public import seed_coverage_zips

    await seed_coverage_zips(db_session)
    token = await _login(client, "addr-cov-no@test.com")

    resp = await client.post(
        "/api/v1/users/me/addresses",
        json={
            "label": "NYC",
            "line1": "350 5th Ave",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "enforce_coverage_check": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["error"]["code"] == "zip_outside_coverage"


@pytest.mark.asyncio
async def test_address_without_enforce_flag_accepts_any_zip(
    client: AsyncClient, stub_geocoder, db_session: AsyncSession,
) -> None:
    """Default (enforce_coverage_check omitted/False) preserves the
    pre-Plan-24 behaviour: any ZIP is accepted. Important for backward
    compat with admin edits + the legacy onboarding tests."""
    from app.db.seed_public import seed_coverage_zips

    await seed_coverage_zips(db_session)
    token = await _login(client, "addr-cov-bypass@test.com")

    # ZIP 99999 is intentionally not seeded — would 422 if the gate
    # were unconditional.
    resp = await client.post(
        "/api/v1/users/me/addresses",
        json={
            "label": "Wherever",
            "line1": "Some St",
            "city": "Nowhere",
            "state": "NV",
            "zip_code": "99999",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
