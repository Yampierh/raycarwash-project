"""
tests/test_users_provider_profile.py — Phase 5 chunk Y2.

Covers /api/v1/users/me/provider-profile* and /provider-status:
activation idempotency, role assignment + token_version bump, KYC
gate on the accepting-bookings toggle, and the deactivate path.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import Role, UserRoleAssociation
from domains.providers.models import ProviderProfile
from domains.users.models import User


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str = "prov@test.com") -> str:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201, reg.text
    onboarding = reg.json()["onboarding_token"]
    phone_suffix = str(abs(hash(email)) % 10_000_000).zfill(7)
    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Provider Tester", "phone_number": f"+155{phone_suffix}"},
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


# ─── Activate ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_activate_creates_profile_and_grants_role(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "prov-activate@test.com")

    resp = await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Test Co"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["business_name"] == "Test Co"
    # Activation must NOT auto-flip accepting=True — KYC gates that.
    assert data["is_accepting_bookings"] is False
    assert data["verification_status"] == "not_submitted"

    # User now has the detailer role.
    user = await _get_user(db_session, "prov-activate@test.com")
    detailer_role = (await db_session.execute(
        select(Role).where(Role.name == "detailer")
    )).scalar_one()
    assoc = (await db_session.execute(
        select(UserRoleAssociation)
        .where(
            UserRoleAssociation.user_id == user.id,
            UserRoleAssociation.role_id == detailer_role.id,
        )
    )).scalar_one_or_none()
    assert assoc is not None, "detailer role must be granted at activation"


@pytest.mark.asyncio
async def test_activate_does_NOT_invalidate_callers_access_token(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Activation grants a new role but must not log the user out —
    the role is read from user.user_roles at DB-level on every
    request, so the access token stays valid and the user can hit
    GET /provider-profile immediately afterwards."""
    token = await _login(client, "prov-tokenversion@test.com")
    user_before = await _get_user(db_session, "prov-tokenversion@test.com")
    initial_version = user_before.token_version

    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Version Bump LLC"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # token_version must NOT have been bumped — that would invalidate
    # the caller's own access token mid-onboarding.
    user_after = await _get_user(db_session, "prov-tokenversion@test.com")
    await db_session.refresh(user_after)
    assert user_after.token_version == initial_version

    # And the existing access token still works for follow-up calls.
    resp = await client.get(
        "/api/v1/users/me/provider-profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_activate_is_idempotent_on_existing_profile(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Calling activate twice should update the existing row in place
    (so the user can effectively edit business name during activation)
    rather than 409."""
    token = await _login(client, "prov-idem@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "First Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Renamed", "service_radius_miles": 50},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["business_name"] == "Renamed"
    assert data["service_radius_miles"] == 50

    user = await _get_user(db_session, "prov-idem@test.com")
    rows = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_activate_requires_step_up(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "prov-nostep@test.com")
    user = await _get_user(db_session, "prov-nostep@test.com")
    user.last_step_up_at = None
    await db_session.commit()

    resp = await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "No Step Co"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "step_up_required"


# ─── Read + Update ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_provider_profile_404_before_activate(
    client: AsyncClient,
) -> None:
    token = await _login(client, "prov-noprofile@test.com")
    resp = await client.get(
        "/api/v1/users/me/provider-profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_provider_profile_updates_fields(
    client: AsyncClient,
) -> None:
    token = await _login(client, "prov-patch@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Original"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.patch(
        "/api/v1/users/me/provider-profile",
        json={"tagline": "Best detailing in town", "bio": "20+ years."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["tagline"] == "Best detailing in town"
    assert data["bio"] == "20+ years."
    # Other fields untouched.
    assert data["business_name"] == "Original"


# ─── Status toggle (KYC gate) ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_toggle_blocked_without_kyc(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "prov-nokyc@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Unverified Co"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.patch(
        "/api/v1/users/me/provider-status",
        json={"is_accepting_bookings": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "kyc_required"


@pytest.mark.asyncio
async def test_status_toggle_allowed_when_kyc_approved(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "prov-kyc@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Verified Co"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Manually flip verification_status — Y5 will own the real Stripe
    # Identity flow; this test only checks the KYC gate logic in Y2.
    user = await _get_user(db_session, "prov-kyc@test.com")
    profile = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalar_one()
    profile.verification_status = "approved"
    await db_session.commit()

    resp = await client.patch(
        "/api/v1/users/me/provider-status",
        json={"is_accepting_bookings": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["is_accepting_bookings"] is True


@pytest.mark.asyncio
async def test_status_toggle_to_false_does_not_require_kyc(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Turning OFF should always be allowed regardless of KYC — the
    detailer might want to pause during onboarding."""
    token = await _login(client, "prov-pauseunverified@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Paused Co"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.patch(
        "/api/v1/users/me/provider-status",
        json={"is_accepting_bookings": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Already false at activation — idempotent no-op, still 200.
    assert resp.status_code == 200


# ─── Deactivate ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deactivate_flips_accepting_bookings_to_false(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "prov-deact@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Will Pause"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Approve + accept first so deactivate has something to flip.
    user = await _get_user(db_session, "prov-deact@test.com")
    profile = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalar_one()
    profile.verification_status = "approved"
    profile.is_accepting_bookings = True
    await db_session.commit()

    resp = await client.post(
        "/api/v1/users/me/provider-profile/deactivate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["is_accepting_bookings"] is False
    # KYC state preserved.
    assert resp.json()["data"]["verification_status"] == "approved"
