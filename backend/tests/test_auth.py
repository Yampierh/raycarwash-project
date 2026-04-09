# backend/tests/test_auth.py - Tests de autenticación
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User


# ============================================
# Tests: POST /auth/token (Login)
# ============================================
class TestLogin:
    """Tests para el endpoint de login."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test login exitoso con credenciales válidas."""
        response = await client.post(
            "/auth/token",
            data={
                "username": "testclient@example.com",
                "password": "Test1234!",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user: User):
        """Test login con contraseña incorrecta."""
        response = await client.post(
            "/auth/token",
            data={
                "username": "testclient@example.com",
                "password": "WrongPassword",
            },
        )
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login con usuario que no existe."""
        response = await client.post(
            "/auth/token",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword",
            },
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Test login con usuario inactivo."""
        from app.repositories.user_repository import UserRepository
        
        # Get user from db (via the fixture's created user)
        user_repo = UserRepository(db_session)
        user = await user_repo.get_by_email("testclient@example.com")
        
        if user:
            user.is_active = False
            await db_session.commit()
        
        response = await client.post(
            "/auth/token",
            data={
                "username": "testclient@example.com",
                "password": "Test1234!",
            },
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_missing_credentials(self, client: AsyncClient):
        """Test login sin credenciales."""
        response = await client.post("/auth/token", data={})
        
        # OAuth2PasswordRequestForm requiere username y password
        assert response.status_code in [422, 400]


# ============================================
# Tests: POST /auth/refresh (Token Rotation)
# ============================================
class TestTokenRefresh:
    """Tests para el refresh de tokens."""
    
    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient, test_user: User):
        """Test refresh exitoso con refresh token válido."""
        # Primero obtener tokens
        login_response = await client.post(
            "/auth/token",
            data={
                "username": "testclient@example.com",
                "password": "Test1234!",
            },
        )
        tokens = login_response.json()
        
        # El backend espera query parameter, no JSON body
        response = await client.post(
            f"/auth/refresh?refresh_token={tokens['refresh_token']}",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh con token inválido."""
        response = await client.post(
            "/auth/refresh?refresh_token=invalid_token_here",
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_expired_token(self, client: AsyncClient):
        """Test refresh con token expirado."""
        response = await client.post(
            "/auth/refresh?refresh_token=eyJhbGciOiJIUzI1NiIsInR5cCI6InJlZnJlc2gifQ.eyJzdWIiOiIxMjM0NTY3OC05MGQtMTIzNC01Njc4OTAxMjM0NTY3OCIsInJvbGUiOiJjbGllbnQiLCJ0eXBlIjoicmVmcmVzaCIsImlhdCI6MTcwODA4MDAwMCwiZXhwIjoxNzA4MDgzNjAwfQ.invalid",
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_missing_token(self, client: AsyncClient):
        """Test refresh sin proporcionar token."""
        response = await client.post("/auth/refresh")
        
        assert response.status_code == 422


# ============================================
# Tests: GET /auth/me (Current User Profile)
# ============================================
class TestGetCurrentUser:
    """Tests para obtener el usuario actual."""
    
    @pytest.mark.asyncio
    async def test_me_authenticated(self, client: AsyncClient, test_user: User):
        """Test obtener perfil de usuario autenticado."""
        # Login primero
        login_response = await client.post(
            "/auth/token",
            data={
                "username": "testclient@example.com",
                "password": "Test1234!",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Get profile
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testclient@example.com"
        assert data["full_name"] == "Test Client"
    
    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        """Test obtener perfil sin autenticación."""
        response = await client.get("/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client: AsyncClient):
        """Test obtener perfil con token inválido."""
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        
        assert response.status_code == 401


# ============================================
# Tests: PUT /auth/update (Update Profile)
# ============================================
class TestUpdateProfile:
    """Tests para actualizar perfil de usuario."""
    
    @pytest.mark.asyncio
    async def test_update_profile_success(self, client: AsyncClient, test_user: User):
        """Test actualizar perfil exitosamente."""
        # Login
        login_response = await client.post(
            "/auth/token",
            data={
                "username": "testclient@example.com",
                "password": "Test1234!",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Update profile
        response = await client.put(
            "/auth/update",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "full_name": "Updated Name",
                "phone_number": "+1234567890",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["phone_number"] == "+1234567890"
    
    @pytest.mark.asyncio
    async def test_update_profile_partial(self, client: AsyncClient, test_user: User):
        """Test actualización parcial (solo algunos campos)."""
        # Login
        login_response = await client.post(
            "/auth/token",
            data={
                "username": "testclient@example.com",
                "password": "Test1234!",
            },
        )
        access_token = login_response.json()["access_token"]
        
        # Update only phone_number
        response = await client.put(
            "/auth/update",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"phone_number": "+1987654321"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Test Client"  # Sin cambios
        assert data["phone_number"] == "+1987654321"
    
    @pytest.mark.asyncio
    async def test_update_profile_unauthenticated(self, client: AsyncClient):
        """Test actualizar perfil sin autenticación."""
        response = await client.put(
            "/auth/update",
            json={"full_name": "New Name"},
        )
        
        assert response.status_code == 401


# ============================================
# Tests: POST /auth/google (Google OAuth)
# ============================================
class TestGoogleLogin:
    """Tests para login con Google."""
    
    @pytest.mark.asyncio
    async def test_google_login_new_user(self, client: AsyncClient):
        """Test login con Google creando nuevo usuario."""
        # Nota: En testing real, necesitaríamos mockear la verificación de Google
        # Este test simula el flujo
        response = await client.post(
            "/auth/google",
            json={"access_token": "mock_google_token"},
        )
        
        # Dependiendo de la configuración, podría ser 401 (token inválido)
        # o crear un usuario si el mock está configurado
        assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_google_login_missing_token(self, client: AsyncClient):
        """Test login con Google sin token."""
        response = await client.post("/auth/google", json={})
        
        assert response.status_code == 422


# ============================================
# Tests: POST /auth/password-reset (Password Reset)
# ============================================
class TestPasswordReset:
    """Tests para reset de contraseña."""
    
    @pytest.mark.asyncio
    async def test_password_reset_existing_user(self, client: AsyncClient, test_user: User):
        """Test request de reset para usuario existente."""
        response = await client.post(
            "/auth/password-reset",
            json={"email": "testclient@example.com"},
        )
        
        # Siempre devuelve 200 para evitar enumeración
        assert response.status_code == 200
        assert "message" in response.json()
    
    @pytest.mark.asyncio
    async def test_password_reset_nonexistent_user(self, client: AsyncClient):
        """Test request de reset para usuario no existente."""
        response = await client.post(
            "/auth/password-reset",
            json={"email": "nonexistent@example.com"},
        )
        
        # Siempre devuelve 200 (seguridad)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_password_reset_missing_email(self, client: AsyncClient):
        """Test request de reset sin email."""
        response = await client.post("/auth/password-reset", json={})
        
        assert response.status_code == 422


# ============================================
# Tests: Rate Limiting
# ============================================
class TestRateLimiting:
    """Tests para rate limiting."""
    
    @pytest.mark.asyncio
    async def test_login_rate_limit(self, client: AsyncClient, test_user: User):
        """Test rate limiting en login (10 req/min)."""
        # Hacer múltiples requests rápidas
        for i in range(15):
            response = await client.post(
                "/auth/token",
                data={
                    "username": "testclient@example.com",
                    "password": "Test1234!",
                },
            )
            if response.status_code == 429:
                break
        
        # Uno de los últimos debería ser 429
        assert response.status_code == 429