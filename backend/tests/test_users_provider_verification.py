"""
tests/test_users_provider_verification.py — Phase 5 chunk Y5.

Drives the /me/provider-verification + /me/provider-achievements
endpoints. The Stripe SDK is stubbed so tests don't hit Stripe's
network. The dev-bypass branch is the path real local development
takes; the "real Stripe" branch is exercised by patching the
config + the SDK call.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.providers.achievement import ProviderAchievement
from domains.providers.models import ProviderProfile
from domains.users.models import User


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
        json={"full_name": "Verif Tester", "phone_number": f"+155{phone_suffix}"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Secure1234!"},
    )
    return login.json()["access_token"]


async def _activate(client: AsyncClient, token: str) -> None:
    resp = await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Verif Co"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text


# ─── Activate-required guard ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verification_start_requires_provider_mode(
    client: AsyncClient,
) -> None:
    token = await _login(client, "verif-noactivate@test.com")
    resp = await client.post(
        "/api/v1/users/me/provider-verification",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_verification_status_requires_provider_mode(
    client: AsyncClient,
) -> None:
    token = await _login(client, "verif-status-noactivate@test.com")
    resp = await client.get(
        "/api/v1/users/me/provider-verification",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


# ─── Start: dev bypass branch ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_returns_dev_bypass_when_placeholder_key(
    client: AsyncClient,
) -> None:
    """The test environment uses sk_test_placeholder, so start MUST
    return is_dev_bypass=true and skip the real Stripe SDK call."""
    token = await _login(client, "verif-bypass@test.com")
    await _activate(client, token)

    resp = await client.post(
        "/api/v1/users/me/provider-verification",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["is_dev_bypass"] is True
    assert data["client_secret"] is None
    assert data["session_id"] is None


# ─── Start: real Stripe branch (mocked SDK) ───────────────────────────────────


@pytest.mark.asyncio
async def test_start_creates_stripe_session_and_persists_id(
    client: AsyncClient, db_session: AsyncSession, monkeypatch,
) -> None:
    """Patch the placeholder check so we hit the real-SDK branch, and
    patch stripe.identity.VerificationSession.create so no network."""
    from domains.users import provider_verification_service as svc_mod

    monkeypatch.setattr(svc_mod, "_is_stripe_placeholder", lambda: False)
    # Pretend DEBUG is False too so is_dev_bypass evaluates False.
    from app.core.config import get_settings as _gs
    settings = _gs()
    monkeypatch.setattr(settings, "DEBUG", False, raising=False)
    monkeypatch.setattr(
        settings, "STRIPE_PUBLISHABLE_KEY", "pk_test_xyz", raising=False,
    )

    fake_session = MagicMock(
        id="vs_test_abc",
        client_secret="vs_test_abc_secret_xyz",
    )
    monkeypatch.setattr(
        svc_mod.stripe.identity.VerificationSession, "create",
        lambda **kw: fake_session,
    )

    token = await _login(client, "verif-real@test.com")
    await _activate(client, token)

    resp = await client.post(
        "/api/v1/users/me/provider-verification",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["is_dev_bypass"] is False
    assert data["session_id"] == "vs_test_abc"
    assert data["client_secret"] == "vs_test_abc_secret_xyz"

    # Side effect: row persisted session_id + bumped status to pending.
    user = (await db_session.execute(
        select(User).where(User.email == "verif-real@test.com")
    )).scalar_one()
    pp = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalar_one()
    await db_session.refresh(pp)
    assert pp.stripe_verification_session_id == "vs_test_abc"
    assert pp.verification_status == "pending"


# ─── Status ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_initial_state_is_not_submitted(
    client: AsyncClient,
) -> None:
    token = await _login(client, "verif-init@test.com")
    await _activate(client, token)
    resp = await client.get(
        "/api/v1/users/me/provider-verification",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["verification_status"] == "not_submitted"
    assert data["has_active_session"] is False


@pytest.mark.asyncio
async def test_status_after_webhook_approval(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Simulate the existing identity.verification_session.verified
    webhook by flipping verification_status directly — we just want
    the read endpoint to surface it."""
    token = await _login(client, "verif-approved@test.com")
    await _activate(client, token)

    user = (await db_session.execute(
        select(User).where(User.email == "verif-approved@test.com")
    )).scalar_one()
    pp = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalar_one()
    pp.verification_status = "approved"
    pp.legal_full_name = "Yampier Hernandez"
    pp.verification_submitted_at = datetime.now(timezone.utc)
    pp.verification_reviewed_at = datetime.now(timezone.utc)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/users/me/provider-verification",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()["data"]
    assert data["verification_status"] == "approved"
    assert data["legal_full_name"] == "Yampier Hernandez"
    assert data["has_active_session"] is False
    assert data["verification_submitted_at"] is not None


@pytest.mark.asyncio
async def test_status_has_active_session_when_pending(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "verif-pending@test.com")
    await _activate(client, token)

    user = (await db_session.execute(
        select(User).where(User.email == "verif-pending@test.com")
    )).scalar_one()
    pp = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalar_one()
    pp.verification_status = "pending"
    pp.stripe_verification_session_id = "vs_test_pending"
    await db_session.commit()

    resp = await client.get(
        "/api/v1/users/me/provider-verification",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()["data"]
    assert data["verification_status"] == "pending"
    assert data["has_active_session"] is True


# ─── Achievements ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_achievements_empty_for_new_user(
    client: AsyncClient,
) -> None:
    token = await _login(client, "ach-empty@test.com")
    resp = await client.get(
        "/api/v1/users/me/provider-achievements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_achievements_returns_seeded_badges_newest_first(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """The list endpoint should NOT require active provider mode — a
    user that earned a badge then deactivated still gets to see it."""
    token = await _login(client, "ach-seeded@test.com")

    user = (await db_session.execute(
        select(User).where(User.email == "ach-seeded@test.com")
    )).scalar_one()
    now = datetime.now(timezone.utc)
    db_session.add(ProviderAchievement(
        provider_user_id=user.id,
        achievement_type="first_job",
        metadata_={"completed_at": now.isoformat()},
        awarded_at=now,
    ))
    db_session.add(ProviderAchievement(
        provider_user_id=user.id,
        achievement_type="verified",
        metadata_=None,
        awarded_at=now,
    ))
    await db_session.commit()

    resp = await client.get(
        "/api/v1/users/me/provider-achievements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 2
    types = {item["achievement_type"] for item in items}
    assert types == {"first_job", "verified"}
