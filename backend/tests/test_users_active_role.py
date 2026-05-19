"""
tests/test_users_active_role.py — Master plan Phase 6 (ADR-003).

End-to-end coverage for PATCH /api/v1/users/me/active-role:
  * caller must already hold the target role (else 403)
  * "admin" is not a switchable target
  * "client" (default) ALWAYS switchable for any registered user
  * refresh is rotated atomically — the old one is dead after the switch
  * new access token carries the target role in its `role` claim
  * audit log records ROLE_SWITCHED with old/new
  * /auth/refresh after a switch preserves the active_role claim
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.audit.models import AuditAction, AuditLog
from domains.auth.models import Role, UserRoleAssociation
from domains.auth.service import AuthService
from domains.users.models import User


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str) -> tuple[str, str]:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201, reg.text
    onboarding = reg.json()["onboarding_token"]
    phone_suffix = str(abs(hash(email)) % 10_000_000).zfill(7)
    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Phase 6 Tester", "phone_number": f"+155{phone_suffix}"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Secure1234!"},
    )
    body = login.json()
    return body["access_token"], body["refresh_token"]


async def _get_user(db: AsyncSession, email: str) -> User:
    return (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one()


async def _grant_role(db: AsyncSession, user: User, role_name: str) -> None:
    role = (await db.execute(
        select(Role).where(Role.name == role_name)
    )).scalar_one()
    db.add(UserRoleAssociation(user_id=user.id, role_id=role.id))
    await db.commit()


def _envelope(resp_json: dict) -> dict:
    assert "data" in resp_json
    return resp_json["data"]


# ─── happy path ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_switch_to_assigned_role_returns_new_tokens(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token, refresh = await _login(client, "p6-switch@test.com")
    user = await _get_user(db_session, "p6-switch@test.com")
    await _grant_role(db_session, user, "detailer")

    resp = await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "detailer", "refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = _envelope(resp.json())
    assert data["active_role"] == "detailer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["access_token"] != token
    assert data["refresh_token"] != refresh


@pytest.mark.asyncio
async def test_new_access_token_carries_target_role(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token, refresh = await _login(client, "p6-claim@test.com")
    user = await _get_user(db_session, "p6-claim@test.com")
    await _grant_role(db_session, user, "detailer")

    resp = await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "detailer", "refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )
    new_access = _envelope(resp.json())["access_token"]
    decoded = AuthService.decode_token(new_access)
    assert decoded["role"] == "detailer"
    assert decoded["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_switch_persists_active_role_on_user(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token, refresh = await _login(client, "p6-persist@test.com")
    user = await _get_user(db_session, "p6-persist@test.com")
    await _grant_role(db_session, user, "mechanic")

    await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "mechanic", "refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )

    await db_session.refresh(user)
    assert user.active_role == "mechanic"


# ─── refresh rotation ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_old_refresh_is_revoked_after_switch(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """The whole point of ADR-003: a refresh stolen before the switch
    can't keep emitting access tokens after."""
    token, old_refresh = await _login(client, "p6-rotate@test.com")
    user = await _get_user(db_session, "p6-rotate@test.com")
    await _grant_role(db_session, user, "detailer")

    await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "detailer", "refresh_token": old_refresh},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Old refresh must be dead now.
    refresh_resp = await client.post(
        "/auth/refresh", params={"refresh_token": old_refresh},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_new_refresh_works_and_preserves_active_role(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """After the switch the new refresh should mint access tokens that
    still carry the target role (Phase 6 also taught /auth/refresh to
    honor user.active_role)."""
    token, refresh = await _login(client, "p6-refresh-preserve@test.com")
    user = await _get_user(db_session, "p6-refresh-preserve@test.com")
    await _grant_role(db_session, user, "detailer")

    switch_resp = await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "detailer", "refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )
    new_refresh = _envelope(switch_resp.json())["refresh_token"]

    refresh_resp = await client.post(
        "/auth/refresh", params={"refresh_token": new_refresh},
    )
    assert refresh_resp.status_code == 200, refresh_resp.text
    decoded = AuthService.decode_token(refresh_resp.json()["access_token"])
    assert decoded["role"] == "detailer"


# ─── 403 paths ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_switch_to_unassigned_role_returns_403(
    client: AsyncClient,
) -> None:
    token, refresh = await _login(client, "p6-unassigned@test.com")

    resp = await client.patch(
        "/api/v1/users/me/active-role",
        # Caller has only "client" — no detailer role yet.
        json={"role": "detailer", "refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "permission_denied"


@pytest.mark.asyncio
async def test_switch_to_admin_rejected_via_pydantic(
    client: AsyncClient,
) -> None:
    """admin is not in the switchable Literal — Pydantic rejects with 422
    before the service even runs."""
    token, refresh = await _login(client, "p6-admin@test.com")

    resp = await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "admin", "refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_switch_unknown_role_rejected(
    client: AsyncClient,
) -> None:
    token, refresh = await _login(client, "p6-unknown@test.com")

    resp = await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "landscaper", "refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_switch_unauthenticated_returns_401(
    client: AsyncClient,
) -> None:
    resp = await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "client", "refresh_token": "irrelevant"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_switch_with_bad_refresh_returns_401(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token, _ = await _login(client, "p6-badrefresh@test.com")
    user = await _get_user(db_session, "p6-badrefresh@test.com")
    await _grant_role(db_session, user, "detailer")

    resp = await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "detailer", "refresh_token": "garbage-not-a-token"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


# ─── client target ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_switching_to_client_works_for_default_user(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Every registered user already holds the client role (assigned in
    complete-profile). Switching to it must therefore succeed."""
    token, refresh = await _login(client, "p6-client-target@test.com")

    resp = await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "client", "refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert _envelope(resp.json())["active_role"] == "client"


# ─── audit log ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_switch_emits_role_switched_audit_row(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token, refresh = await _login(client, "p6-audit@test.com")
    user = await _get_user(db_session, "p6-audit@test.com")
    await _grant_role(db_session, user, "detailer")

    await client.patch(
        "/api/v1/users/me/active-role",
        json={"role": "detailer", "refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )

    rows = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.actor_id == user.id,
            AuditLog.action == AuditAction.ROLE_SWITCHED,
        )
    )).scalars().all()
    assert len(rows) == 1
    entry = rows[0]
    assert entry.entity_type == "user"
    assert entry.new_value == {"active_role": "detailer"}
    # old_value can be None (no prior switch) — assert it's present in
    # the row but tolerate both None and {"active_role": None}.
    assert entry.old_value in (None, {"active_role": None})
