"""
tests/test_e1c_providers_profiles.py — Integration plan E1 chunk C.

End-to-end coverage for `/api/v1/providers/profiles` — the multi-profile
self-service endpoints introduced in E1.C. Distinct from
`/api/v1/users/me/provider-profile*` (Phase 5) which is detailer-only.

Each test runs against a real PostgreSQL fixture and goes through the
full register → complete-profile → login dance via `_login`.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import Role, UserRoleAssociation
from domains.providers.models import ProviderProfile, ProviderType
from domains.users.models import User


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str = "e1c@test.com") -> str:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201, reg.text
    onboarding = reg.json()["onboarding_token"]
    phone_suffix = str(abs(hash(email)) % 10_000_000).zfill(7)
    await client.put(
        "/auth/complete-profile",
        json={"full_name": "E1C Tester", "phone_number": f"+155{phone_suffix}"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Secure1234!"},
    )
    return login.json()["access_token"]


async def _get_user(db_session: AsyncSession, email: str) -> User:
    return (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()


async def _expire_step_up(db_session: AsyncSession, email: str) -> None:
    user = await _get_user(db_session, email)
    user.last_step_up_at = None
    await db_session.commit()


def _envelope(resp_json: dict) -> dict:
    assert "data" in resp_json, f"missing data: {resp_json}"
    return resp_json["data"]


# ─── Create ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_detailer_profile_grants_role(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "e1c-create-detailer@test.com")

    resp = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer", "business_name": "Detail Co"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = _envelope(resp.json())
    assert data["provider_type"] == "detailer"
    assert data["business_name"] == "Detail Co"
    # is_active starts False — KYC gates the public surface.
    assert data["is_active"] is False
    assert data["is_accepting_bookings"] is False
    assert data["verification_status"] == "not_submitted"

    user = await _get_user(db_session, "e1c-create-detailer@test.com")
    detailer_role = (await db_session.execute(
        select(Role).where(Role.name == "detailer")
    )).scalar_one()
    assoc = (await db_session.execute(
        select(UserRoleAssociation).where(
            UserRoleAssociation.user_id == user.id,
            UserRoleAssociation.role_id == detailer_role.id,
        )
    )).scalar_one_or_none()
    assert assoc is not None


@pytest.mark.asyncio
async def test_create_mechanic_profile_grants_mechanic_role(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "e1c-create-mech@test.com")

    resp = await client.post(
        "/api/v1/providers/profiles",
        json={
            "provider_type": "mechanic",
            "business_name": "Mech Co",
            "tagline": "Wrench whisperer",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = _envelope(resp.json())
    assert data["provider_type"] == "mechanic"

    user = await _get_user(db_session, "e1c-create-mech@test.com")
    mechanic_role = (await db_session.execute(
        select(Role).where(Role.name == "mechanic")
    )).scalar_one()
    assoc = (await db_session.execute(
        select(UserRoleAssociation).where(
            UserRoleAssociation.user_id == user.id,
            UserRoleAssociation.role_id == mechanic_role.id,
        )
    )).scalar_one_or_none()
    assert assoc is not None


@pytest.mark.asyncio
async def test_create_duplicate_type_returns_409(
    client: AsyncClient,
) -> None:
    token = await _login(client, "e1c-dup@test.com")

    first = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer", "business_name": "First"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer", "business_name": "Second"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "already_exists"


@pytest.mark.asyncio
async def test_create_supports_dual_profiles(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """A single user can hold a DETAILER + MECHANIC profile side by side."""
    token = await _login(client, "e1c-dual@test.com")

    r1 = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer", "business_name": "Detail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "mechanic", "business_name": "Mech"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 201

    user = await _get_user(db_session, "e1c-dual@test.com")
    rows = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalars().all()
    assert {p.provider_type for p in rows} == {"detailer", "mechanic"}


@pytest.mark.asyncio
async def test_create_rejects_unknown_provider_type(
    client: AsyncClient,
) -> None:
    token = await _login(client, "e1c-bad-type@test.com")

    resp = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "landscaper"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_create_requires_step_up(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "e1c-nostep@test.com")
    await _expire_step_up(db_session, "e1c-nostep@test.com")

    resp = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "step_up_required"


# ─── List + Get ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_returns_all_owned_profiles(client: AsyncClient) -> None:
    token = await _login(client, "e1c-list@test.com")
    await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "mechanic"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/providers/profiles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = _envelope(resp.json())
    assert {p["provider_type"] for p in data} == {"detailer", "mechanic"}


@pytest.mark.asyncio
async def test_list_returns_empty_when_no_profiles(client: AsyncClient) -> None:
    token = await _login(client, "e1c-empty@test.com")
    resp = await client.get(
        "/api/v1/providers/profiles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert _envelope(resp.json()) == []


@pytest.mark.asyncio
async def test_get_specific_profile_by_id(client: AsyncClient) -> None:
    token = await _login(client, "e1c-getone@test.com")
    created = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer", "business_name": "Got One"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = created.json()["data"]["id"]

    resp = await client.get(
        f"/api/v1/providers/profiles/{profile_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert _envelope(resp.json())["business_name"] == "Got One"


@pytest.mark.asyncio
async def test_get_other_users_profile_returns_404(
    client: AsyncClient,
) -> None:
    """Ownership leak guard — a profile that belongs to another user must
    return 404, not 403, so existence stays hidden."""
    # User A creates profile
    token_a = await _login(client, "e1c-owner-a@test.com")
    created = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    profile_id = created.json()["data"]["id"]

    # User B tries to read it
    token_b = await _login(client, "e1c-owner-b@test.com")
    resp = await client.get(
        f"/api/v1/providers/profiles/{profile_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404, resp.text


# ─── Patch ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_updates_fields(client: AsyncClient) -> None:
    token = await _login(client, "e1c-patch@test.com")
    created = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer", "business_name": "Original"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = created.json()["data"]["id"]

    resp = await client.patch(
        f"/api/v1/providers/profiles/{profile_id}",
        json={"business_name": "Renamed", "tagline": "Best in town"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = _envelope(resp.json())
    assert data["business_name"] == "Renamed"
    assert data["tagline"] == "Best in town"


@pytest.mark.asyncio
async def test_patch_activation_requires_kyc(client: AsyncClient) -> None:
    """Flipping is_active=True without KYC must 403 kyc_required."""
    token = await _login(client, "e1c-kyc@test.com")
    created = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = created.json()["data"]["id"]

    resp = await client.patch(
        f"/api/v1/providers/profiles/{profile_id}",
        json={"is_active": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "kyc_required"


@pytest.mark.asyncio
async def test_patch_deactivation_does_not_require_kyc(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Flipping is_active=False is always allowed — pause never needs KYC."""
    token = await _login(client, "e1c-deact@test.com")
    created = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = created.json()["data"]["id"]

    # Bypass KYC at the DB level so we can flip is_active=True manually.
    pp = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.id == profile_id)
    )).scalar_one()
    pp.verification_status = "approved"
    pp.is_active = True
    pp.is_accepting_bookings = True
    await db_session.commit()

    resp = await client.patch(
        f"/api/v1/providers/profiles/{profile_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = _envelope(resp.json())
    assert data["is_active"] is False
    # Dual-write check — is_accepting_bookings must follow.
    assert data["is_accepting_bookings"] is False


@pytest.mark.asyncio
async def test_patch_other_users_profile_returns_404(
    client: AsyncClient,
) -> None:
    token_a = await _login(client, "e1c-patch-a@test.com")
    created = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    profile_id = created.json()["data"]["id"]

    token_b = await _login(client, "e1c-patch-b@test.com")
    resp = await client.patch(
        f"/api/v1/providers/profiles/{profile_id}",
        json={"business_name": "Hacker"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


# ─── Delete ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_soft_deletes_profile(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "e1c-del@test.com")
    created = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "mechanic"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = created.json()["data"]["id"]

    resp = await client.delete(
        f"/api/v1/providers/profiles/{profile_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    # Row should still exist with is_deleted=True (soft delete, not hard).
    import uuid as _uuid
    pp = (await db_session.execute(
        select(ProviderProfile).where(
            ProviderProfile.id == _uuid.UUID(profile_id)
        )
    )).scalar_one()
    assert pp.is_deleted is True

    # And it disappears from the list endpoint.
    list_resp = await client.get(
        "/api/v1/providers/profiles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert _envelope(list_resp.json()) == []


@pytest.mark.asyncio
async def test_re_enroll_same_type_after_soft_delete_returns_409(
    client: AsyncClient,
) -> None:
    """
    Current contract: re-enrolling in the same vertical after a soft
    delete returns 409 because the composite unique (user_id,
    provider_type) is plain (not partial). The soft-deleted row still
    occupies the slot. Switching to a partial index `WHERE is_deleted
    = FALSE` would let re-enrollment work without losing the historical
    row — see TODO below.

    TODO(integrations/01-phase2): make uq_provider_profiles_user_type a
    partial unique index that ignores soft-deleted rows. The migration
    is small (drop + create with WHERE is_deleted=false) but requires a
    second pass on the service to either reuse the old row or fully
    accept the new one. Out of E1.C scope.
    """
    token = await _login(client, "e1c-reenroll@test.com")
    created = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "mechanic"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = created.json()["data"]["id"]

    await client.delete(
        f"/api/v1/providers/profiles/{profile_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "mechanic", "business_name": "Back Again"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "already_exists"


@pytest.mark.asyncio
async def test_after_soft_delete_other_type_still_allowed(
    client: AsyncClient,
) -> None:
    """Soft-deleting the DETAILER profile must not block creating a
    MECHANIC profile — the composite unique is keyed by both fields."""
    token = await _login(client, "e1c-cross-type@test.com")
    created = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "detailer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    detailer_id = created.json()["data"]["id"]
    await client.delete(
        f"/api/v1/providers/profiles/{detailer_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.post(
        "/api/v1/providers/profiles",
        json={"provider_type": "mechanic", "business_name": "Switched"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
