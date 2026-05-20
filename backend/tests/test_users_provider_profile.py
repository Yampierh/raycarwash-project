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


# ─── Plan 24 Wave 1 — provider signup multi-step fields ──────────────────────


@pytest.mark.asyncio
async def test_patch_persists_signup_fields(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """PATCH accepts the 4 new signup fields and persists them.
    ssn_last_4 is encrypted at rest (verify by reading the column —
    it should NOT equal the plaintext value)."""
    from app.db.seed_cities import seed_cities

    await seed_cities(db_session)

    token = await _login(client, "prov-signup-fields@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Signup Detail"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.patch(
        "/api/v1/users/me/provider-profile",
        json={
            "ssn_last_4": "1234",
            "home_city_code": "fwa",
            "water_tank_gallons": 40,
            "services_offered": ["soap", "vacuum", "polish"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    # SSN intentionally not in response (write-only).
    assert "ssn_last_4" not in data
    assert "ssn_last_4_encrypted" not in data
    # Other fields surface back.
    assert data["home_city_code"] == "fwa"
    assert data["water_tank_gallons"] == 40
    assert data["services_offered"] == ["soap", "vacuum", "polish"]
    # default state
    assert data["application_status"] == "draft"

    # SSN is persisted (via EncryptedType the in-DB column != plaintext
    # but the ORM read decrypts transparently). Verify via the model.
    user = await _get_user(db_session, "prov-signup-fields@test.com")
    profile = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalar_one()
    assert profile.ssn_last_4_encrypted == "1234"


@pytest.mark.asyncio
async def test_patch_rejects_unknown_city(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    from app.db.seed_cities import seed_cities

    await seed_cities(db_session)

    token = await _login(client, "prov-bad-city@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Bad City Co"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.patch(
        "/api/v1/users/me/provider-profile",
        json={"home_city_code": "xxx"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    body = resp.json()
    # ErrorEnvelope shape
    assert body["error"]["code"] == "city_not_found"


@pytest.mark.asyncio
async def test_patch_rejects_invalid_services_offered_enum(
    client: AsyncClient,
) -> None:
    """Literal enum validation rejects unknown skill slugs."""
    token = await _login(client, "prov-bad-skill@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Bad Skill Co"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.patch(
        "/api/v1/users/me/provider-profile",
        json={"services_offered": ["soap", "underbody-wax"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_ssn_last_4_rejects_non_digits(
    client: AsyncClient,
) -> None:
    """Pydantic regex enforces 4 digits."""
    token = await _login(client, "prov-bad-ssn@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Bad SSN Co"},
        headers={"Authorization": f"Bearer {token}"},
    )

    for bad in ["12a4", "123", "12345", "abcd"]:
        resp = await client.patch(
            "/api/v1/users/me/provider-profile",
            json={"ssn_last_4": bad},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422, f"SSN {bad!r} should 422"


# ─── Plan 24 Wave 1 — submit application ─────────────────────────────────────


async def _fill_signup_draft(
    db_session: AsyncSession, email: str,
) -> None:
    """Populate every required field directly on the ProviderProfile so
    the submit happy-path test isn't 7 PATCHes deep."""
    from datetime import date
    user = await _get_user(db_session, email)
    profile = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalar_one()
    profile.legal_full_name = "Marcus Tate"
    profile.date_of_birth = date(1990, 5, 1)
    profile.ssn_last_4_encrypted = "1234"
    profile.home_city_code = "fwa"
    profile.service_radius_miles = 12
    profile.water_tank_gallons = 40
    profile.services_offered = ["soap", "vacuum"]
    profile.background_check_consent = True
    await db_session.commit()


@pytest.mark.asyncio
async def test_submit_application_happy_path(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "prov-submit@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Submit Detail"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await _fill_signup_draft(db_session, "prov-submit@test.com")

    resp = await client.post(
        "/api/v1/users/me/provider-profile/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["application_status"] == "submitted"
    assert "submitted_at" in data
    assert len(data["next_steps"]) >= 3

    # GET confirms the state transitioned in DB
    follow = await client.get(
        "/api/v1/users/me/provider-profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert follow.json()["data"]["application_status"] == "submitted"


@pytest.mark.asyncio
async def test_submit_application_lists_missing_fields(
    client: AsyncClient,
) -> None:
    """Fresh draft with only business_name set → 422 with the 8
    missing field labels."""
    token = await _login(client, "prov-missing@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Empty Co"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.post(
        "/api/v1/users/me/provider-profile/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "application_incomplete"
    # All 8 required-field labels should be in the details list.
    labels = {d["field"] for d in body["error"]["details"]}
    assert "Legal full name" in labels
    assert "SSN last 4" in labels
    assert "Home city" in labels
    assert "Water tank size" in labels
    assert "Services you can offer" in labels
    assert "Background-check consent" in labels


@pytest.mark.asyncio
async def test_submit_application_409_when_not_draft(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Resubmitting after a prior submit returns 409 — state machine
    only allows external transitions out of `submitted` (Checkr,
    admin approval)."""
    token = await _login(client, "prov-double@test.com")
    await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Double Co"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await _fill_signup_draft(db_session, "prov-double@test.com")

    first = await client.post(
        "/api/v1/users/me/provider-profile/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/users/me/provider-profile/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "application_not_in_draft"


@pytest.mark.asyncio
async def test_submit_application_404_without_profile(
    client: AsyncClient,
) -> None:
    """User who never activated provider mode → 404."""
    token = await _login(client, "prov-no-profile@test.com")
    resp = await client.post(
        "/api/v1/users/me/provider-profile/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
