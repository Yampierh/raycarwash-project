"""
test_user_flows.py

End-to-end registration and onboarding flows for CLIENT and DETAILER roles.

Covers:
  - Full client registration: register → complete-profile (role=client) → login → /auth/me
  - Full detailer registration: register → complete-profile (role=detailer) → login → /auth/me
  - Guard rails: wrong role, re-completion blocked, onboarding token scope isolation
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _register(client: AsyncClient, email: str, password: str = "Secure1234!") -> dict:
    resp = await client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    return resp.json()


async def _complete_profile(
    client: AsyncClient,
    onboarding_token: str,
    full_name: str,
    phone: str,
    service_type: str | None = None,  # "Detailer" → detailer role; None → client
) -> dict:
    payload: dict = {"full_name": full_name, "phone_number": phone}
    if service_type:
        payload["service_type"] = service_type
    resp = await client.put(
        "/auth/complete-profile",
        json=payload,
        headers={"Authorization": f"Bearer {onboarding_token}"},
    )
    assert resp.status_code == 200, f"complete-profile failed: {resp.text}"
    return resp.json()


async def _login(client: AsyncClient, email: str, password: str = "Secure1234!") -> dict:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()


async def _approve_kyc(db_session: AsyncSession, email: str) -> None:
    """Simulate KYC approval for a detailer in tests.

    Looks up user by email, creates IdentityVerification (APPROVED) and
    marks OnboardingState as COMPLETED.  Called after complete-profile to
    set up a fully-onboarded detailer without needing the admin endpoint.
    """
    from domains.identity.models import IdentityVerification, KycStatus
    from domains.onboarding.models import OnboardingState
    from domains.users.models import User
    from domains.users.repository import UserRepository

    user = await UserRepository(db_session).get_by_email(email)
    if user is None:
        return

    identity = IdentityVerification(
        user_id=user.id,
        status=KycStatus.APPROVED.value,
        document_data={"id_front_url": "test", "selfie_url": "test"},
    )
    db_session.add(identity)

    stmt = select(OnboardingState).where(OnboardingState.user_id == user.id)
    result = await db_session.execute(stmt)
    state = result.scalar_one_or_none()
    if state:
        from domains.onboarding.state import OnboardingStep
        state.status = OnboardingStep.COMPLETED.value
        state.current_step = None
        state.completed = True

    user.onboarding_status = "completed"

    await db_session.flush()


async def _me(client: AsyncClient, access_token: str) -> dict:
    resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200, f"/auth/me failed: {resp.text}"
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT FLOW
# ─────────────────────────────────────────────────────────────────────────────

class TestClientRegistrationFlow:

    @pytest.mark.asyncio
    async def test_register_returns_onboarding_token_not_access_token(self, client: AsyncClient):
        data = await _register(client, "client1@example.com")
        assert data["onboarding_token"] is not None
        assert data["access_token"] is None
        assert data["refresh_token"] is None
        assert data["next_step"] == "complete_profile"

    @pytest.mark.asyncio
    async def test_complete_profile_client_returns_full_tokens(self, client: AsyncClient):
        reg = await _register(client, "client2@example.com")
        # No service_type → defaults to client role
        prof = await _complete_profile(
            client, reg["onboarding_token"], "Alice Smith", "+12605550101"
        )
        assert prof["access_token"] is not None
        assert prof["refresh_token"] is not None
        assert prof["next_step"] == "app"
        assert prof["assigned_role"] == "client"

    @pytest.mark.asyncio
    async def test_client_can_login_after_onboarding(self, client: AsyncClient):
        reg = await _register(client, "client3@example.com")
        await _complete_profile(
            client, reg["onboarding_token"], "Bob Jones", "+12605550102"
        )
        login = await _login(client, "client3@example.com")
        assert login["access_token"] is not None
        assert login["refresh_token"] is not None

    @pytest.mark.asyncio
    async def test_client_me_returns_correct_role(self, client: AsyncClient):
        reg = await _register(client, "client4@example.com")
        await _complete_profile(
            client, reg["onboarding_token"], "Carol White", "+12605550103"
        )
        login = await _login(client, "client4@example.com")
        me = await _me(client, login["access_token"])

        assert me["email"] == "client4@example.com"
        assert me["full_name"] == "Carol White"
        assert "client" in me["roles"]
        assert me["onboarding_completed"] is True

    @pytest.mark.asyncio
    async def test_client_phone_stored_correctly(self, client: AsyncClient):
        phone = "+12605550104"
        reg = await _register(client, "client5@example.com")
        await _complete_profile(
            client, reg["onboarding_token"], "Dave Brown", phone
        )
        login = await _login(client, "client5@example.com")
        me = await _me(client, login["access_token"])
        assert me["phone_number"] == phone

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        await _register(client, "dup@example.com")
        resp = await client.post(
            "/auth/register", json={"email": "dup@example.com", "password": "Secure1234!"}
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_onboarding_token_blocked_on_protected_endpoints(self, client: AsyncClient):
        """Onboarding token must not grant access to regular endpoints.
        The endpoint returns 401 because get_current_user rejects the onboarding scope."""
        reg = await _register(client, "blocked@example.com")
        onboarding_token = reg["onboarding_token"]
        resp = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {onboarding_token}"}
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_complete_profile_twice_returns_403(self, client: AsyncClient):
        """Once onboarded, calling complete-profile again must be blocked."""
        reg = await _register(client, "doublecomplete@example.com")
        tok = reg["onboarding_token"]
        await _complete_profile(client, tok, "First Try", "+12605550105")

        # Login to get a real access token, then attempt re-completion
        login = await _login(client, "doublecomplete@example.com")
        resp = await client.put(
            "/auth/complete-profile",
            json={"full_name": "Second Try", "phone_number": "+12605550105"},
            headers={"Authorization": f"Bearer {login['access_token']}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_login_before_completing_profile_returns_onboarding_token(
        self, client: AsyncClient
    ):
        """Login with incomplete user → returns onboarding_token, not access_token."""
        await _register(client, "incomplete@example.com")
        resp = await client.post(
            "/auth/login",
            json={"email": "incomplete@example.com", "password": "Secure1234!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("onboarding_token") is not None
        assert data.get("access_token") is None


# ─────────────────────────────────────────────────────────────────────────────
# DETAILER FLOW
# ─────────────────────────────────────────────────────────────────────────────

class TestDetailerRegistrationFlow:

    @pytest.mark.asyncio
    async def test_register_detailer_returns_onboarding_token(self, client: AsyncClient):
        data = await _register(client, "detailer1@example.com")
        assert data["onboarding_token"] is not None
        assert data["next_step"] == "complete_profile"

    @pytest.mark.asyncio
    async def test_complete_profile_detailer_returns_temp_token_not_access(self, client: AsyncClient):
        reg = await _register(client, "detailer2@example.com")
        prof = await _complete_profile(
            client,
            reg["onboarding_token"],
            "Emma Detail",
            "+12605550201",
            service_type="Detailer",
        )
        assert prof["access_token"] is None
        assert prof["temp_token"] is not None
        assert prof["assigned_role"] == "detailer"
        assert prof["needs_profile_completion"] is True

    @pytest.mark.asyncio
    async def test_detailer_me_returns_detailer_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        reg = await _register(client, "detailer3@example.com")
        await _complete_profile(
            client,
            reg["onboarding_token"],
            "Frank Detail",
            "+12605550202",
            service_type="Detailer",
        )
        await _approve_kyc(db_session, "detailer3@example.com")

        login = await _login(client, "detailer3@example.com")
        me = await _me(client, login["access_token"])

        assert me["email"] == "detailer3@example.com"
        assert "detailer" in me["roles"]
        assert me["onboarding_completed"] is True

    @pytest.mark.asyncio
    async def test_detailer_does_not_get_client_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        reg = await _register(client, "detailer4@example.com")
        await _complete_profile(
            client,
            reg["onboarding_token"],
            "Grace Detail",
            "+12605550203",
            service_type="Detailer",
        )
        await _approve_kyc(db_session, "detailer4@example.com")

        login = await _login(client, "detailer4@example.com")
        me = await _me(client, login["access_token"])
        assert "client" not in me["roles"]
        assert "detailer" in me["roles"]

    @pytest.mark.asyncio
    async def test_detailer_login_after_onboarding(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        reg = await _register(client, "detailer5@example.com")
        await _complete_profile(
            client,
            reg["onboarding_token"],
            "Henry Detail",
            "+12605550204",
            service_type="Detailer",
        )
        await _approve_kyc(db_session, "detailer5@example.com")

        login = await _login(client, "detailer5@example.com")
        assert login["access_token"] is not None
        assert login["onboarding_completed"] is True

    @pytest.mark.asyncio
    async def test_cannot_escalate_to_admin_via_service_type(
        self, client: AsyncClient
    ):
        """service_type is validated — only 'Detailer' is a valid service type.
        Passing an unknown service_type like 'Admin' must be rejected with 422."""
        reg = await _register(client, "escalate@example.com")
        resp = await client.put(
            "/auth/complete-profile",
            json={
                "full_name": "Hacker",
                "phone_number": "+12605550299",
                "service_type": "Admin",  # not a valid VALID_SERVICE_TYPES value
            },
            headers={"Authorization": f"Bearer {reg['onboarding_token']}"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_detailer_and_client_are_different_accounts(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Two separate users — one client, one detailer — have distinct roles."""
        reg_c = await _register(client, "sep_client@example.com")
        await _complete_profile(
            client, reg_c["onboarding_token"], "Sep Client", "+12605550301"
        )

        reg_d = await _register(client, "sep_detailer@example.com")
        await _complete_profile(
            client,
            reg_d["onboarding_token"],
            "Sep Detailer",
            "+12605550302",
            service_type="Detailer",
        )
        await _approve_kyc(db_session, "sep_detailer@example.com")

        login_c = await _login(client, "sep_client@example.com")
        login_d = await _login(client, "sep_detailer@example.com")

        me_c = await _me(client, login_c["access_token"])
        me_d = await _me(client, login_d["access_token"])

        assert "client" in me_c["roles"]
        assert "detailer" not in me_c["roles"]
        assert "detailer" in me_d["roles"]
        assert "client" not in me_d["roles"]
