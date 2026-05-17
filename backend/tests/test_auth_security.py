"""
tests/test_auth_security.py — /api/v1/auth/security, /history, /two-fa
and /passkeys (Phase 3 chunk O).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from domains.users.models import User


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str, password: str = "Secure1234!") -> str:
    reg = await client.post(
        "/auth/register", json={"email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    onboarding = reg.json()["onboarding_token"]
    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Security Tester", "phone_number": "+15553330000"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": password},
    )
    return login.json()["access_token"]


async def _grant_step_up(db_session: AsyncSession, email: str) -> None:
    await db_session.execute(
        update(User).where(User.email == email).values(
            last_step_up_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()


async def _expire_step_up(db_session: AsyncSession, email: str) -> None:
    """Push last_step_up_at outside the window so the next step-up-gated
    request 401s. Needed after Hotfix H3, which now populates the column
    on login — pre-H3 it was always NULL by accident."""
    await db_session.execute(
        update(User).where(User.email == email).values(last_step_up_at=None)
    )
    await db_session.commit()


# ─── /auth/security ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_security_summary_baseline(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "sec-baseline@test.com")
    # Hotfix H3 made /auth/login populate last_step_up_at, so a freshly
    # logged-in user has step_up_recent=True. To exercise the "no step-up"
    # branch of the summary we explicitly expire the column first.
    await _expire_step_up(db_session, "sec-baseline@test.com")
    resp = await client.get(
        "/api/v1/auth/security",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["has_password"] is True
    assert data["two_factor_enabled"] is False
    assert data["passkeys_count"] == 0
    assert data["active_sessions_count"] >= 1
    assert data["step_up_recent"] is False


# ─── /auth/two-fa enrollment + verify ────────────────────────────────────────


@pytest.mark.asyncio
async def test_two_fa_enroll_returns_secret_and_codes(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "totp-enroll@test.com")
    await _grant_step_up(db_session, "totp-enroll@test.com")

    resp = await client.post(
        "/api/v1/auth/two-fa/enroll",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert len(data["secret"]) >= 16
    assert data["otpauth_uri"].startswith("otpauth://totp/")
    assert len(data["backup_codes"]) == 10
    # Backup codes have the X1Y2-Z3W4 shape.
    for code in data["backup_codes"]:
        assert len(code) == 9 and code[4] == "-"


@pytest.mark.asyncio
async def test_two_fa_full_flow_enables(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "totp-flow@test.com")
    await _grant_step_up(db_session, "totp-flow@test.com")

    enroll = await client.post(
        "/api/v1/auth/two-fa/enroll",
        headers={"Authorization": f"Bearer {token}"},
    )
    secret = enroll.json()["data"]["secret"]
    code = pyotp.TOTP(secret).now()

    verify = await client.post(
        "/api/v1/auth/two-fa/verify",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify.status_code == 200, verify.text
    summary = verify.json()["data"]
    assert summary["two_factor_enabled"] is True

    # Confirm the standalone /security endpoint also reports it.
    sec = await client.get(
        "/api/v1/auth/security",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sec.json()["data"]["two_factor_enabled"] is True


@pytest.mark.asyncio
async def test_two_fa_verify_rejects_bad_code(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "totp-bad@test.com")
    await _grant_step_up(db_session, "totp-bad@test.com")

    await client.post(
        "/api/v1/auth/two-fa/enroll",
        headers={"Authorization": f"Bearer {token}"},
    )
    verify = await client.post(
        "/api/v1/auth/two-fa/verify",
        json={"code": "000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify.status_code == 422, verify.text


@pytest.mark.asyncio
async def test_two_fa_backup_code_accepted_in_place_of_otp(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "totp-backup@test.com")
    await _grant_step_up(db_session, "totp-backup@test.com")

    enroll = await client.post(
        "/api/v1/auth/two-fa/enroll",
        headers={"Authorization": f"Bearer {token}"},
    )
    backup_code = enroll.json()["data"]["backup_codes"][0]

    verify = await client.post(
        "/api/v1/auth/two-fa/verify",
        json={"code": backup_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify.status_code == 200, verify.text


@pytest.mark.asyncio
async def test_two_fa_disable_drops_credential(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "totp-disable@test.com")
    await _grant_step_up(db_session, "totp-disable@test.com")

    enroll = await client.post(
        "/api/v1/auth/two-fa/enroll",
        headers={"Authorization": f"Bearer {token}"},
    )
    secret = enroll.json()["data"]["secret"]
    code = pyotp.TOTP(secret).now()
    await client.post(
        "/api/v1/auth/two-fa/verify",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
    )

    delete = await client.delete(
        "/api/v1/auth/two-fa",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete.status_code == 204, delete.text

    sec = await client.get(
        "/api/v1/auth/security",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sec.json()["data"]["two_factor_enabled"] is False


@pytest.mark.asyncio
async def test_two_fa_enroll_blocks_without_step_up(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "totp-nostep@test.com")
    # Post-H3 the login auto-bumps last_step_up_at; expire it so this
    # test still exercises the "no recent step-up" rejection path.
    await _expire_step_up(db_session, "totp-nostep@test.com")
    resp = await client.post(
        "/api/v1/auth/two-fa/enroll",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "step_up_required"


@pytest.mark.asyncio
async def test_two_fa_regenerate_requires_enabled(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "totp-regen@test.com")
    await _grant_step_up(db_session, "totp-regen@test.com")

    # Not enabled yet → 409
    resp = await client.post(
        "/api/v1/auth/two-fa/backup-codes/regenerate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text


# ─── /auth/history ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_security_history_lists_login_events(client: AsyncClient) -> None:
    token = await _login(client, "history@test.com")
    resp = await client.get(
        "/api/v1/auth/history?limit=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]
    # At least one login row should be visible from the successful
    # _login() above.
    assert len(items) >= 1
    types = {i["type"] for i in items}
    assert "login" in types
