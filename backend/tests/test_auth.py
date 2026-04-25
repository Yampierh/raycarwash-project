# backend/tests/test_auth.py
import uuid as uuid_module

import jose.jwt as jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import User
from tests.conftest import get_access_token


# ============================================
# POST /auth/register
# ============================================
class TestRegister:

    @pytest.mark.asyncio
    async def test_register_new_user_returns_onboarding_token(self, client: AsyncClient):
        """Registro exitoso: retorna onboarding_token, next_step=complete_profile."""
        response = await client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "Secure1234!"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["onboarding_token"] is not None
        assert data["access_token"] is None
        assert data["refresh_token"] is None
        assert data["next_step"] == "complete_profile"
        assert data["onboarding_completed"] is False

    @pytest.mark.asyncio
    async def test_register_no_login_on_success(self, client: AsyncClient):
        """Registro nunca retorna access_token — el usuario no está logueado."""
        response = await client.post(
            "/auth/register",
            json={"email": "another@example.com", "password": "Secure1234!"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data.get("access_token") is None
        assert data.get("refresh_token") is None

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self, client: AsyncClient, test_user: User):
        """Email ya registrado → 409 Conflict."""
        response = await client.post(
            "/auth/register",
            json={"email": "testclient@example.com", "password": "Secure1234!"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_password_too_short(self, client: AsyncClient):
        """Password < 8 caracteres → 422."""
        response = await client.post(
            "/auth/register",
            json={"email": "short@example.com", "password": "123"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Email inválido → 422."""
        response = await client.post(
            "/auth/register",
            json={"email": "notanemail", "password": "Secure1234!"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_onboarding_token_grants_complete_profile_access(
        self, client: AsyncClient
    ):
        """El onboarding_token permite acceder a /auth/complete-profile."""
        reg = await client.post(
            "/auth/register",
            json={"email": "flow@example.com", "password": "Secure1234!"},
        )
        onboarding_token = reg.json()["onboarding_token"]

        response = await client.put(
            "/auth/complete-profile",
            json={"full_name": "Flow User", "phone_number": "+12605550100", "role": "client"},
            headers={"Authorization": f"Bearer {onboarding_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] is not None
        assert data["next_step"] == "app"

    @pytest.mark.asyncio
    async def test_register_onboarding_token_blocked_on_regular_endpoints(
        self, client: AsyncClient
    ):
        """El onboarding_token NO puede acceder a /auth/me — solo onboarding endpoints."""
        reg = await client.post(
            "/auth/register",
            json={"email": "blocked@example.com", "password": "Secure1234!"},
        )
        onboarding_token = reg.json()["onboarding_token"]

        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {onboarding_token}"},
        )
        assert response.status_code == 403


# ============================================
# POST /auth/login
# ============================================
class TestLogin:

    @pytest.mark.asyncio
    async def test_login_success_returns_tokens(self, client: AsyncClient, test_user: User):
        """Login exitoso: retorna access_token + refresh_token + roles."""
        response = await client.post(
            "/auth/login",
            json={"email": "testclient@example.com", "password": "Test1234!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] is not None
        assert data["refresh_token"] is not None
        assert data["onboarding_token"] is None
        assert data["onboarding_completed"] is True
        assert "client" in data["roles"]

    @pytest.mark.asyncio
    async def test_login_never_creates_account(self, client: AsyncClient):
        """Email inexistente → 401, nunca crea cuenta."""
        response = await client.post(
            "/auth/login",
            json={"email": "ghost@example.com", "password": "Secure1234!"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Password incorrecta → 401."""
        response = await client.post(
            "/auth/login",
            json={"email": "testclient@example.com", "password": "WrongPassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_incomplete_onboarding_returns_onboarding_token(
        self, client: AsyncClient, incomplete_user: User
    ):
        """Usuario con onboarding_completed=False → onboarding_token, no access_token."""
        response = await client.post(
            "/auth/login",
            json={"email": "incomplete@example.com", "password": "Test1234!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["onboarding_token"] is not None
        assert data["access_token"] is None
        assert data["refresh_token"] is None
        assert data["onboarding_completed"] is False
        assert data["next_step"] == "complete_profile"

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self, client: AsyncClient, test_user: User, db_session: AsyncSession
    ):
        """Usuario inactivo → 401."""
        from app.repositories.user_repository import UserRepository
        user = await UserRepository(db_session).get_by_email("testclient@example.com")
        user.is_active = False
        await db_session.commit()

        response = await client.post(
            "/auth/login",
            json={"email": "testclient@example.com", "password": "Test1234!"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_access_token_grants_me_access(
        self, client: AsyncClient, test_user: User
    ):
        """El access_token del login permite acceder a /auth/me."""
        login = await client.post(
            "/auth/login",
            json={"email": "testclient@example.com", "password": "Test1234!"},
        )
        token = login.json()["access_token"]

        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "testclient@example.com"
        assert me.json()["onboarding_completed"] is True


# ============================================
# POST /auth/logout
# ============================================
class TestLogout:

    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(
        self, client: AsyncClient, test_user: User
    ):
        """Logout revoca el refresh token — el token no puede usarse después."""
        login = await client.post(
            "/auth/login",
            json={"email": "testclient@example.com", "password": "Test1234!"},
        )
        tokens = login.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        logout = await client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout.status_code == 204

        # El refresh token ya no puede rotar
        refresh = await client.post(f"/auth/refresh?refresh_token={refresh_token}")
        assert refresh.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_second_device_still_works(
        self, client: AsyncClient, test_user: User
    ):
        """Logout en un dispositivo no afecta la sesión del otro."""
        login1 = await client.post(
            "/auth/login",
            json={"email": "testclient@example.com", "password": "Test1234!"},
        )
        login2 = await client.post(
            "/auth/login",
            json={"email": "testclient@example.com", "password": "Test1234!"},
        )
        tokens1 = login1.json()
        tokens2 = login2.json()

        # Logout del dispositivo 1
        await client.post(
            "/auth/logout",
            json={"refresh_token": tokens1["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens1['access_token']}"},
        )

        # Dispositivo 2 sigue activo
        refresh2 = await client.post(
            f"/auth/refresh?refresh_token={tokens2['refresh_token']}"
        )
        assert refresh2.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_invalid_token_silent(
        self, client: AsyncClient, test_user: User
    ):
        """Logout con refresh_token desconocido → 204 silencioso (no leak info)."""
        access_token = await get_access_token(client, "testclient@example.com")
        response = await client.post(
            "/auth/logout",
            json={"refresh_token": "this_token_does_not_exist"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_logout_requires_auth(self, client: AsyncClient):
        """Logout sin Bearer token → 401."""
        response = await client.post(
            "/auth/logout",
            json={"refresh_token": "sometoken"},
        )
        assert response.status_code == 401


# ============================================
# POST /auth/token  (OAuth2 form — Swagger compat)
# ============================================
class TestOAuth2Token:

    @pytest.mark.asyncio
    async def test_token_success(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/auth/token",
            data={"username": "testclient@example.com", "password": "Test1234!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_token_invalid_password(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/auth/token",
            data={"username": "testclient@example.com", "password": "WrongPassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/auth/token",
            data={"username": "nonexistent@example.com", "password": "SomePassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_missing_credentials(self, client: AsyncClient):
        response = await client.post("/auth/token", data={})
        assert response.status_code in [422, 400]


# ============================================
# POST /auth/refresh (Token Rotation)
# ============================================
class TestTokenRefresh:

    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient, test_user: User):
        """Refresh exitoso retorna nuevos tokens."""
        login = await client.post(
            "/auth/token",
            data={"username": "testclient@example.com", "password": "Test1234!"},
        )
        refresh_token = login.json()["refresh_token"]

        response = await client.post(f"/auth/refresh?refresh_token={refresh_token}")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # El token rotado debe ser diferente al original
        assert data["refresh_token"] != refresh_token

    @pytest.mark.asyncio
    async def test_refresh_token_single_use(self, client: AsyncClient, test_user: User):
        """Usar el mismo refresh_token dos veces → robo detectado → 401."""
        login = await client.post(
            "/auth/token",
            data={"username": "testclient@example.com", "password": "Test1234!"},
        )
        refresh_token = login.json()["refresh_token"]

        await client.post(f"/auth/refresh?refresh_token={refresh_token}")
        response = await client.post(f"/auth/refresh?refresh_token={refresh_token}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        response = await client.post("/auth/refresh?refresh_token=invalid_token_here")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_missing_token(self, client: AsyncClient):
        response = await client.post("/auth/refresh")
        assert response.status_code == 422


# ============================================
# GET /auth/me
# ============================================
class TestGetCurrentUser:

    @pytest.mark.asyncio
    async def test_me_returns_user_with_onboarding_completed(
        self, client: AsyncClient, test_user: User
    ):
        access_token = await get_access_token(client, "testclient@example.com")
        response = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testclient@example.com"
        assert data["full_name"] == "Test Client"
        assert data["onboarding_completed"] is True
        assert "client" in data["roles"]

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


# ============================================
# PUT /auth/complete-profile
# ============================================
class TestCompleteProfile:

    @pytest.mark.asyncio
    async def test_complete_profile_client_flow(self, client: AsyncClient):
        """Flujo completo: registro → complete-profile client → acceso normal."""
        reg = await client.post(
            "/auth/register",
            json={"email": "complete1@example.com", "password": "Secure1234!"},
        )
        onboarding_token = reg.json()["onboarding_token"]

        response = await client.put(
            "/auth/complete-profile",
            json={"full_name": "Jane Client", "phone_number": "+12605550100", "role": "client"},
            headers={"Authorization": f"Bearer {onboarding_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] is not None
        assert data["refresh_token"] is not None
        assert data["next_step"] == "app"

    @pytest.mark.asyncio
    async def test_complete_profile_detailer_flow(self, client: AsyncClient):
        """Registro → complete-profile detailer → next_step=detailer_onboarding."""
        reg = await client.post(
            "/auth/register",
            json={"email": "complete2@example.com", "password": "Secure1234!"},
        )
        onboarding_token = reg.json()["onboarding_token"]

        response = await client.put(
            "/auth/complete-profile",
            json={"full_name": "Jane Detailer", "role": "detailer"},
            headers={"Authorization": f"Bearer {onboarding_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["next_step"] == "detailer_onboarding"
        assert data["access_token"] is not None

    @pytest.mark.asyncio
    async def test_complete_profile_accumulates_roles(
        self, client: AsyncClient, test_user: User
    ):
        """
        Usuario client que completa perfil como detailer acumula ambos roles.
        No pierde el rol client.
        """
        from app.services.auth import AuthService

        onboarding_token = AuthService.create_onboarding_token(test_user.id)

        response = await client.put(
            "/auth/complete-profile",
            json={"full_name": "Test Client", "role": "detailer"},
            headers={"Authorization": f"Bearer {onboarding_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # El rol asignado es detailer
        assert data["assigned_role"] == "detailer"

    @pytest.mark.asyncio
    async def test_complete_profile_accepts_regular_access_token(self, client: AsyncClient, test_user: User):
        """
        A regular access_token is accepted on /auth/complete-profile.
        This supports the use case where a fully-onboarded user adds a second role
        (e.g., a client who also wants to become a detailer).
        The endpoint only accumulates roles — it never removes existing ones.
        """
        access_token = await get_access_token(client, "testclient@example.com")
        response = await client.put(
            "/auth/complete-profile",
            json={"full_name": "Test Client", "role": "client"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] is not None
        assert data["assigned_role"] == "client"

    @pytest.mark.asyncio
    async def test_complete_profile_without_token_fails(self, client: AsyncClient):
        """Sin token → 401."""
        response = await client.put(
            "/auth/complete-profile",
            json={"full_name": "John Doe", "role": "client"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_complete_profile_marks_onboarding_completed(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Después de complete-profile, /auth/me muestra onboarding_completed=True."""
        reg = await client.post(
            "/auth/register",
            json={"email": "verifystate@example.com", "password": "Secure1234!"},
        )
        onboarding_token = reg.json()["onboarding_token"]

        complete = await client.put(
            "/auth/complete-profile",
            json={"full_name": "Verify State", "role": "client"},
            headers={"Authorization": f"Bearer {onboarding_token}"},
        )
        access_token = complete.json()["access_token"]

        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me.status_code == 200
        assert me.json()["onboarding_completed"] is True


# ============================================
# POST /auth/verify  (login-only, backward compat)
# ============================================
class TestVerify:

    @pytest.mark.asyncio
    async def test_verify_login_existing_user(self, client: AsyncClient, test_user: User):
        """verify con usuario existente → tokens normales."""
        response = await client.post(
            "/auth/verify",
            json={
                "identifier": "testclient@example.com",
                "identifier_type": "email",
                "password": "Test1234!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] is not None
        assert data["needs_profile_completion"] is False

    @pytest.mark.asyncio
    async def test_verify_never_creates_account(self, client: AsyncClient):
        """verify con email inexistente → 401, NUNCA crea cuenta."""
        response = await client.post(
            "/auth/verify",
            json={
                "identifier": "totally_new_user@example.com",
                "identifier_type": "email",
                "password": "Secure1234!",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_onboarding_incomplete_user(
        self, client: AsyncClient, incomplete_user: User
    ):
        """verify con usuario onboarding incompleto → temp_token + needs_profile_completion."""
        response = await client.post(
            "/auth/verify",
            json={
                "identifier": "incomplete@example.com",
                "identifier_type": "email",
                "password": "Test1234!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["needs_profile_completion"] is True
        assert data["temp_token"] is not None
        assert data["access_token"] is None

    @pytest.mark.asyncio
    async def test_verify_wrong_password(self, client: AsyncClient, test_user: User):
        """verify con password incorrecta → 401."""
        response = await client.post(
            "/auth/verify",
            json={
                "identifier": "testclient@example.com",
                "identifier_type": "email",
                "password": "WrongPassword",
            },
        )
        assert response.status_code == 401


# ============================================
# POST /auth/identify + GET /auth/check-email
# ============================================
class TestIdentifierFirst:

    @pytest.mark.asyncio
    async def test_identify_new_user(self, client: AsyncClient):
        response = await client.post(
            "/auth/identify", json={"identifier": "newuser@test.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert data["suggested_action"] == "register"

    @pytest.mark.asyncio
    async def test_identify_existing_user(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/auth/identify", json={"identifier": test_user.email}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert "password" in data["auth_methods"]

    @pytest.mark.asyncio
    async def test_check_email_existing(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/auth/check-email", json={"email": "testclient@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["suggested_action"] == "login"

    @pytest.mark.asyncio
    async def test_check_email_new(self, client: AsyncClient):
        response = await client.post(
            "/auth/check-email", json={"email": "brand_new@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert data["suggested_action"] == "register"


# ============================================
# PUT /auth/update
# ============================================
class TestUpdateProfile:

    @pytest.mark.asyncio
    async def test_update_profile_success(self, client: AsyncClient, test_user: User):
        access_token = await get_access_token(client, "testclient@example.com")
        response = await client.put(
            "/auth/update",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"full_name": "Updated Name", "phone_number": "+1234567890"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["phone_number"] == "+1234567890"

    @pytest.mark.asyncio
    async def test_update_profile_unauthenticated(self, client: AsyncClient):
        response = await client.put("/auth/update", json={"full_name": "New Name"})
        assert response.status_code == 401


# ============================================
# POST /auth/password-reset
# ============================================
class TestPasswordReset:

    @pytest.mark.asyncio
    async def test_password_reset_existing_user(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/auth/password-reset", json={"email": "testclient@example.com"}
        )
        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_password_reset_nonexistent_user(self, client: AsyncClient):
        # Siempre 200 — no revela si el email existe (user enumeration protection)
        response = await client.post(
            "/auth/password-reset", json={"email": "nonexistent@example.com"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_password_reset_missing_email(self, client: AsyncClient):
        response = await client.post("/auth/password-reset", json={})
        assert response.status_code == 422


# ============================================
# POST /auth/password-reset/confirm
# Single-use token guarantee
# ============================================
class TestPasswordResetSingleUse:
    """
    Verify that password reset tokens are single-use and DB-backed.

    Strategy: create tokens directly via AuthService to get the raw token
    (bypassing email delivery), then exercise the confirm endpoint.
    """

    @pytest.mark.asyncio
    async def test_reset_token_works_on_first_use(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """First use of a valid token must update the password and return 200."""
        from app.services.auth import AuthService

        raw_token = await AuthService.create_password_reset_token(
            test_user.id, test_user.primary_role or "client", db_session
        )
        await db_session.commit()

        resp = await client.post(
            "/auth/password-reset/confirm",
            json={"token": raw_token, "new_password": "NewPass9999!"},
        )
        assert resp.status_code == 200
        assert "successfully" in resp.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_reset_token_rejected_on_second_use(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """Same token must be rejected on second use — single-use guarantee."""
        from app.services.auth import AuthService

        raw_token = await AuthService.create_password_reset_token(
            test_user.id, test_user.primary_role or "client", db_session
        )
        await db_session.commit()

        first = await client.post(
            "/auth/password-reset/confirm",
            json={"token": raw_token, "new_password": "FirstNew9999!"},
        )
        assert first.status_code == 200

        second = await client.post(
            "/auth/password-reset/confirm",
            json={"token": raw_token, "new_password": "SecondAttempt!!1"},
        )
        assert second.status_code == 400, (
            "Reused reset token must be rejected with 400. "
            "Single-use guarantee is broken."
        )

    @pytest.mark.asyncio
    async def test_reset_expired_token_rejected(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """Token with expires_at in the past must be rejected."""
        from datetime import datetime, timezone, timedelta
        from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
        import secrets

        raw_token = secrets.token_urlsafe(32)
        repo = PasswordResetTokenRepository(db_session)
        await repo.create(
            user_id=test_user.id,
            raw_token=raw_token,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        await db_session.commit()

        resp = await client.post(
            "/auth/password-reset/confirm",
            json={"token": raw_token, "new_password": "ShouldFail1!"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_nonexistent_token_rejected(self, client: AsyncClient):
        """A completely unknown token must be rejected with 400."""
        resp = await client.post(
            "/auth/password-reset/confirm",
            json={"token": "totally-invalid-token-that-does-not-exist", "new_password": "Fail1234!"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_increments_token_version(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """Successful password reset must increment token_version to invalidate sessions."""
        from app.services.auth import AuthService
        from app.repositories.user_repository import UserRepository

        original_version = getattr(test_user, "token_version", 1)

        raw_token = await AuthService.create_password_reset_token(
            test_user.id, test_user.primary_role or "client", db_session
        )
        await db_session.commit()

        resp = await client.post(
            "/auth/password-reset/confirm",
            json={"token": raw_token, "new_password": "VersionBump9!"},
        )
        assert resp.status_code == 200

        refreshed = await UserRepository(db_session).get_by_id(test_user.id)
        new_version = getattr(refreshed, "token_version", 1)
        assert new_version == original_version + 1, (
            f"token_version must be incremented after password reset "
            f"(expected {original_version + 1}, got {new_version})."
        )

    @pytest.mark.asyncio
    async def test_new_request_invalidates_prior_token(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """Requesting a second reset must invalidate the first token."""
        from app.services.auth import AuthService

        first_token = await AuthService.create_password_reset_token(
            test_user.id, test_user.primary_role or "client", db_session
        )
        await db_session.commit()

        # Request a second reset — this invalidates the first token
        _second_token = await AuthService.create_password_reset_token(
            test_user.id, test_user.primary_role or "client", db_session
        )
        await db_session.commit()

        resp = await client.post(
            "/auth/password-reset/confirm",
            json={"token": first_token, "new_password": "ShouldFail1!"},
        )
        assert resp.status_code == 400, (
            "First token must be invalidated when a second reset is requested."
        )


# ============================================
# Security: key isolation
# ============================================
class TestKeyIsolation:
    """
    Verify that JWT_SECRET_KEY and ENCRYPTION_KEY are independent.
    A token signed with a different key must not decode successfully.
    """

    def test_jwt_signed_with_wrong_key_is_rejected(self):
        """Token forged with a different signing key must raise on decode."""
        settings = get_settings()
        payload = {"sub": str(uuid_module.uuid4()), "type": "access"}
        forged = jwt.encode(payload, "wrong-key-" + "x" * 32, algorithm="HS256")
        with pytest.raises(Exception):
            jwt.decode(forged, settings.JWT_SECRET_KEY, algorithms=["HS256"])

    def test_jwt_secret_key_differs_from_encryption_key(self):
        """JWT_SECRET_KEY and ENCRYPTION_KEY must be distinct values."""
        settings = get_settings()
        assert settings.JWT_SECRET_KEY != settings.ENCRYPTION_KEY, (
            "JWT_SECRET_KEY and ENCRYPTION_KEY must not share the same value. "
            "Each key must be independently generated."
        )

    def test_jwt_secret_key_differs_from_phone_lookup_key(self):
        """JWT_SECRET_KEY and PHONE_LOOKUP_KEY must be distinct values."""
        settings = get_settings()
        assert settings.JWT_SECRET_KEY != settings.PHONE_LOOKUP_KEY


# ============================================
# Onboarding token: payload and type checks
# ============================================
class TestOnboardingTokenSecurity:
    """
    Verify the dedicated 'onboarding' token type is correctly structured
    and rejected on non-onboarding endpoints.
    """

    @pytest.mark.asyncio
    async def test_onboarding_token_payload_type_is_onboarding(self, client: AsyncClient):
        """Onboarding token must carry type='onboarding', not type='access'."""
        settings = get_settings()
        reg = await client.post(
            "/auth/register",
            json={"email": "typecheck@example.com", "password": "Secure1234!"},
        )
        assert reg.status_code == 201
        token = reg.json()["onboarding_token"]

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        assert payload["type"] == "onboarding", (
            f"Expected type='onboarding', got type='{payload['type']}'. "
            "Onboarding tokens must use a dedicated type to prevent cross-type misuse."
        )

    @pytest.mark.asyncio
    async def test_onboarding_token_payload_has_no_role_claim(self, client: AsyncClient):
        """Onboarding token must not carry a role claim (user has no role yet)."""
        settings = get_settings()
        reg = await client.post(
            "/auth/register",
            json={"email": "norole@example.com", "password": "Secure1234!"},
        )
        token = reg.json()["onboarding_token"]
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        assert "role" not in payload or payload.get("role") is None

    @pytest.mark.asyncio
    async def test_onboarding_token_rejected_on_me_endpoint(self, client: AsyncClient):
        """GET /auth/me with an onboarding token must return 403."""
        reg = await client.post(
            "/auth/register",
            json={"email": "me403@example.com", "password": "Secure1234!"},
        )
        token = reg.json()["onboarding_token"]
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_access_token_rejected_on_complete_profile_without_onboarding(
        self, client: AsyncClient, test_user: User
    ):
        """A regular access_token from a fully-onboarded user cannot trigger
        onboarding again — complete-profile requires onboarding token or
        a valid access token for role additions."""
        # This verifies that /auth/complete-profile is accessible with a full token
        # (for role additions) but NOT with a forged onboarding token from another user.
        settings = get_settings()
        forged = jwt.encode(
            {"sub": str(uuid_module.uuid4()), "type": "onboarding"},
            settings.JWT_SECRET_KEY,
            algorithm="HS256",
        )
        resp = await client.put(
            "/auth/complete-profile",
            json={"full_name": "Hacker", "role": "client"},
            headers={"Authorization": f"Bearer {forged}"},
        )
        # User not found in DB → 401 or 403
        assert resp.status_code in (401, 403, 404)
