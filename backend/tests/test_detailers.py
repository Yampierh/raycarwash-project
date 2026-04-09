# backend/tests/test_detailers.py - Tests de detailers
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, DetailerProfile, Service


# ============================================
# Fixtures
# ============================================
async def get_auth_headers(client: AsyncClient, email: str, password: str) -> dict:
    """Helper para obtener headers de autenticación."""
    response = await client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.fixture
async def detailer_with_profile(db_session: AsyncSession, test_detailer: User) -> User:
    """Detailer con perfil completo."""
    profile = DetailerProfile(
        user_id=test_detailer.id,
        bio="Expert detailer with 5 years experience",
        years_of_experience=5,
        service_radius_miles=25,
        timezone="America/Indiana/Indianapolis",
        is_accepting_bookings=True,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(test_detailer)
    return test_detailer


@pytest.fixture
async def test_service(db_session: AsyncSession) -> Service:
    """Create a test service."""
    service = Service(
        name="Premium Detail",
        description="Full premium detailing service",
        base_price_cents=15000,
        base_duration_minutes=120,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)
    return service


# ============================================
# Tests: GET /api/v1/detailers (Public List)
# ============================================
class TestListDetailers:
    """Tests para listar detailers."""
    
    @pytest.mark.asyncio
    async def test_list_detailers_empty(self, client: AsyncClient):
        """Test listar cuando no hay detailers."""
        response = await client.get("/api/v1/detailers")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_list_detailers_with_geo(self, client: AsyncClient, detailer_with_profile: User):
        """Test listar con filtro geográfico."""
        response = await client.get(
            "/api/v1/detailers",
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                "radius_miles": 50,
            },
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_list_detailers_pagination(self, client: AsyncClient, detailer_with_profile: User):
        """Test paginación."""
        response = await client.get(
            "/api/v1/detailers",
            params={"page": 1, "page_size": 10},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "total" in data
    
    @pytest.mark.asyncio
    async def test_list_detailers_min_rating(self, client: AsyncClient, detailer_with_profile: User):
        """Test filtro por rating mínimo."""
        response = await client.get(
            "/api/v1/detailers",
            params={"min_rating": 4.0},
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_list_detailers_lat_lng_required_together(self, client: AsyncClient):
        """Test que lat y lng deben estar juntos."""
        response = await client.get(
            "/api/v1/detailers",
            params={"lat": 41.0793},  # Sin lng
        )
        
        assert response.status_code == 422


# ============================================
# Tests: GET /api/v1/detailers/me (Own Profile)
# ============================================
class TestGetMyProfile:
    """Tests para obtener propio perfil."""
    
    @pytest.mark.asyncio
    async def test_get_my_profile_success(self, client: AsyncClient, detailer_with_profile: User):
        """Test detailer obtiene su propio perfil."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/detailers/me",
            headers=headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Test Detailer"
        assert "average_rating" in data
    
    @pytest.mark.asyncio
    async def test_get_my_profile_not_found(self, client: AsyncClient, test_detailer: User):
        """Test cuando el detailer no tiene perfil creado."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/detailers/me",
            headers=headers,
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_my_profile_as_client_forbidden(self, client: AsyncClient, test_user: User):
        """Test que cliente no puede acceder a /me."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/detailers/me",
            headers=headers,
        )
        
        assert response.status_code == 403


# ============================================
# Tests: PUT /api/v1/detailers/me (Upsert Profile)
# ============================================
class TestUpsertProfile:
    """Tests para crear/actualizar perfil."""
    
    @pytest.mark.asyncio
    async def test_create_profile_success(self, client: AsyncClient, test_detailer: User):
        """Test crear perfil exitosamente."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.put(
            "/api/v1/detailers/me",
            headers=headers,
            json={
                "bio": "New detailer profile",
                "years_of_experience": 3,
                "service_radius_miles": 30,
                "timezone": "America/Indiana/Indianapolis",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == "New detailer profile"
        assert data["years_of_experience"] == 3
    
    @pytest.mark.asyncio
    async def test_update_profile_success(self, client: AsyncClient, detailer_with_profile: User):
        """Test actualizar perfil existente."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.put(
            "/api/v1/detailers/me",
            headers=headers,
            json={
                "bio": "Updated bio",
                "years_of_experience": 10,
                "service_radius_miles": 50,
                "timezone": "America/New_York",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == "Updated bio"
    
    @pytest.mark.asyncio
    async def test_upsert_profile_as_client_forbidden(self, client: AsyncClient, test_user: User):
        """Test que cliente no puede crear perfil."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.put(
            "/api/v1/detailers/me",
            headers=headers,
            json={
                "bio": "Test",
                "years_of_experience": 1,
                "service_radius_miles": 10,
                "timezone": "America/Indiana/Indianapolis",
            },
        )
        
        assert response.status_code == 403


# ============================================
# Tests: PATCH /api/v1/detailers/me/status (Toggle Status)
# ============================================
class TestToggleStatus:
    """Tests para togglear accepting bookings."""
    
    @pytest.mark.asyncio
    async def test_disable_accepting_bookings(
        self,
        client: AsyncClient,
        detailer_with_profile: User
    ):
        """Test desactivar accepting bookings."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.patch(
            "/api/v1/detailers/me/status",
            headers=headers,
            json={"is_accepting_bookings": False},
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_enable_accepting_bookings(
        self,
        client: AsyncClient,
        detailer_with_profile: User
    ):
        """Test activar accepting bookings."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        # First disable
        await client.patch(
            "/api/v1/detailers/me/status",
            headers=headers,
            json={"is_accepting_bookings": False},
        )
        
        # Then enable
        response = await client.patch(
            "/api/v1/detailers/me/status",
            headers=headers,
            json={"is_accepting_bookings": True},
        )
        
        assert response.status_code == 200


# ============================================
# Tests: GET /api/v1/detailers/me/services (List Services)
# ============================================
class TestListMyServices:
    """Tests para listar servicios del detailer."""
    
    @pytest.mark.asyncio
    async def test_list_services_empty(
        self,
        client: AsyncClient,
        detailer_with_profile: User
    ):
        """Test listar servicios cuando no tiene ninguno activo."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/detailers/me/services",
            headers=headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_list_services_with_platform_services(
        self,
        client: AsyncClient,
        detailer_with_profile: User,
        test_service: Service
    ):
        """Test que retorna todos los servicios de la plataforma."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/detailers/me/services",
            headers=headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        # Debe incluir servicios de la plataforma aunque no estén activos para el detailer
        assert any(s["service_id"] == str(test_service.id) for s in data)


# ============================================
# Tests: PATCH /api/v1/detailers/me/services/{id} (Toggle Service)
# ============================================
class TestToggleService:
    """Tests para activar/desactivar servicio."""
    
    @pytest.mark.asyncio
    async def test_activate_service(
        self,
        client: AsyncClient,
        detailer_with_profile: User,
        test_service: Service
    ):
        """Test activar un servicio."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.patch(
            f"/api/v1/detailers/me/services/{test_service.id}",
            headers=headers,
            json={
                "is_active": True,
                "custom_price_cents": 18000,  # Custom price
            },
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_deactivate_service(
        self,
        client: AsyncClient,
        detailer_with_profile: User,
        test_service: Service
    ):
        """Test desactivar un servicio."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        # First activate
        await client.patch(
            f"/api/v1/detailers/me/services/{test_service.id}",
            headers=headers,
            json={"is_active": True},
        )
        
        # Then deactivate
        response = await client.patch(
            f"/api/v1/detailers/me/services/{test_service.id}",
            headers=headers,
            json={"is_active": False},
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_toggle_nonexistent_service(
        self,
        client: AsyncClient,
        detailer_with_profile: User
    ):
        """Test togglear servicio que no existe."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        fake_service_id = str(uuid.uuid4())
        response = await client.patch(
            f"/api/v1/detailers/me/services/{fake_service_id}",
            headers=headers,
            json={"is_active": True},
        )
        
        assert response.status_code == 404


# ============================================
# Tests: GET /api/v1/detailers/{id}/availability (Availability)
# ============================================
class TestAvailability:
    """Tests para disponibilidad de slots."""
    
    @pytest.mark.asyncio
    async def test_get_availability_success(
        self,
        client: AsyncClient,
        detailer_with_profile: User
    ):
        """Test obtener disponibilidad."""
        response = await client.get(
            f"/api/v1/detailers/{detailer_with_profile.id}/availability",
            params={"request_date": "2025-12-20"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_availability_with_service(
        self,
        client: AsyncClient,
        detailer_with_profile: User,
        test_service: Service
    ):
        """Test disponibilidad con servicio específico."""
        response = await client.get(
            f"/api/v1/detailers/{detailer_with_profile.id}/availability",
            params={
                "request_date": "2025-12-20",
                "service_id": str(test_service.id),
                "vehicle_size": "medium",
            },
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_availability_invalid_date(self, client: AsyncClient, detailer_with_profile: User):
        """Test con fecha inválida."""
        response = await client.get(
            f"/api/v1/detailers/{detailer_with_profile.id}/availability",
            params={"request_date": "invalid-date"},
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_availability_past_date(self, client: AsyncClient, detailer_with_profile: User):
        """Test con fecha pasada."""
        response = await client.get(
            f"/api/v1/detailers/{detailer_with_profile.id}/availability",
            params={"request_date": "2020-01-01"},
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_availability_service_requires_vehicle_size(
        self,
        client: AsyncClient,
        detailer_with_profile: User,
        test_service: Service
    ):
        """Test que service_id requiere vehicle_size."""
        response = await client.get(
            f"/api/v1/detailers/{detailer_with_profile.id}/availability",
            params={
                "request_date": "2025-12-20",
                "service_id": str(test_service.id),
                # Falta vehicle_size
            },
        )
        
        assert response.status_code == 422


# ============================================
# Tests: POST /api/v1/detailers/location (Update Location)
# ============================================
class TestUpdateLocation:
    """Tests para actualizar ubicación GPS."""
    
    @pytest.mark.asyncio
    async def test_update_location_success(
        self,
        client: AsyncClient,
        detailer_with_profile: User
    ):
        """Test actualizar ubicación exitosamente."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.post(
            "/api/v1/detailers/location",
            headers=headers,
            json={
                "latitude": 41.0793,
                "longitude": -85.1394,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] == 41.0793
        assert data["longitude"] == -85.1394
    
    @pytest.mark.asyncio
    async def test_update_location_as_client_forbidden(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test que cliente no puede actualizar ubicación."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.post(
            "/api/v1/detailers/location",
            headers=headers,
            json={
                "latitude": 41.0793,
                "longitude": -85.1394,
            },
        )
        
        assert response.status_code == 403


# ============================================
# Tests: GET /api/v1/detailers/{id}/profile (Public Profile)
# ============================================
class TestPublicProfile:
    """Tests para perfil público."""
    
    @pytest.mark.asyncio
    async def test_get_public_profile_success(
        self,
        client: AsyncClient,
        detailer_with_profile: User
    ):
        """Test obtener perfil público."""
        response = await client.get(
            f"/api/v1/detailers/{detailer_with_profile.id}/profile",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "bio" in data
    
    @pytest.mark.asyncio
    async def test_get_public_profile_not_found(self, client: AsyncClient):
        """Test perfil que no existe."""
        fake_uuid = str(uuid.uuid4())
        response = await client.get(
            f"/api/v1/detailers/{fake_uuid}/profile",
        )
        
        assert response.status_code == 404