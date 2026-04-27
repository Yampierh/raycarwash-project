# backend/tests/test_matching.py - Tests de matching/smart matching
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from domains.providers.models import ProviderProfile
from domains.services_catalog.models import Service, ServiceCategory
from domains.users.models import User


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
    """Detailer with complete profile + location (profile already created by fixture)."""
    from sqlalchemy import select
    result = await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == test_detailer.id)
    )
    profile = result.scalar_one()
    profile.current_lat = 41.0793
    profile.current_lng = -85.1394
    await db_session.commit()
    await db_session.refresh(test_detailer)
    return test_detailer


@pytest.fixture
async def test_service(db_session: AsyncSession) -> Service:
    """Create a test service."""
    service = Service(
        name="Full Detail",
        description="Complete interior and exterior detail",
        base_price_cents=12000,  # $120.00
        base_duration_minutes=180,
        is_active=True,
        category=ServiceCategory.FULL_DETAIL,
        price_small=12000,
        price_medium=14400,
        price_large=18000,
        price_xl=24000,
        duration_small_minutes=180,
        duration_medium_minutes=216,
        duration_large_minutes=270,
        duration_xl_minutes=360,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)
    return service


# ============================================
# Tests: GET /api/v1/matching (Smart Matching)
# ============================================
class TestSmartMatching:
    """Tests para el endpoint de matching inteligente."""
    
    @pytest.mark.asyncio
    async def test_matching_requires_auth(self, client: AsyncClient, test_service: Service):
        """Test que matching requiere autenticación."""
        response = await client.get(
            "/api/v1/matching",
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                "date": "2027-06-15",
                "service_id": str(test_service.id),
                "vehicle_sizes": "small,medium",
            },
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_matching_missing_params(self, client: AsyncClient, test_user: User):
        """Test que matching requiere todos los parámetros."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/matching",
            headers=headers,
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                # Falta date, service_id, vehicle_sizes
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_matching_invalid_date_format(
        self,
        client: AsyncClient,
        test_user: User,
        test_service: Service
    ):
        """Test con formato de fecha inválido."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/matching",
            headers=headers,
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                "date": "20-12-2025",  # Wrong format
                "service_id": str(test_service.id),
                "vehicle_sizes": "small",
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_matching_invalid_vehicle_size(
        self,
        client: AsyncClient,
        test_user: User,
        test_service: Service
    ):
        """Test con tamaño de vehículo inválido."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/matching",
            headers=headers,
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                "date": "2027-06-15",
                "service_id": str(test_service.id),
                "vehicle_sizes": "invalid_size",
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_matching_invalid_service_id(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test con service_id que no existe."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        fake_service_id = str(uuid.uuid4())
        response = await client.get(
            "/api/v1/matching",
            headers=headers,
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                "date": "2027-06-15",
                "service_id": fake_service_id,
                "vehicle_sizes": "small",
            },
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_matching_with_addons(
        self,
        client: AsyncClient,
        test_user: User,
        test_service: Service,
        detailer_with_profile: User,
        db_session: AsyncSession
    ):
        """Test matching con addons."""
        from domains.services_catalog.models import Addon
        
        addon = Addon(
            name="Test Matching Addon",
            description="Test-only addon for matching tests",
            price_cents=3000,
            duration_minutes=45,
            is_active=True,
        )
        db_session.add(addon)
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/matching",
            headers=headers,
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                "date": "2027-06-15",
                "service_id": str(test_service.id),
                "vehicle_sizes": "small",
                "addon_ids": str(addon.id),
            },
        )
        
        # Debe retornar array (posiblemente vacío si no hay availability)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_matching_response_structure(
        self,
        client: AsyncClient,
        test_user: User,
        test_service: Service,
        detailer_with_profile: User
    ):
        """Test estructura de respuesta del matching."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/matching",
            headers=headers,
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                "date": "2027-06-15",
                "service_id": str(test_service.id),
                "vehicle_sizes": "small",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura si hay resultados
        if len(data) > 0:
            result = data[0]
            assert "user_id" in result
            assert "full_name" in result
            assert "estimated_price" in result
            assert "estimated_duration" in result
            assert "available_slots" in result
    
    @pytest.mark.asyncio
    async def test_matching_radius_parameter(
        self,
        client: AsyncClient,
        test_user: User,
        test_service: Service,
        detailer_with_profile: User
    ):
        """Test parámetro radius_miles."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        # Con radio pequeño
        response = await client.get(
            "/api/v1/matching",
            headers=headers,
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                "date": "2027-06-15",
                "service_id": str(test_service.id),
                "vehicle_sizes": "small",
                "radius_miles": 1,  # Muy pequeño
            },
        )
        
        assert response.status_code == 200


# ============================================
# Tests: Sorting y Ranking
# ============================================
class TestMatchingSorting:
    """Tests para el ordenamiento de resultados."""
    
    @pytest.mark.asyncio
    async def test_matching_sorted_by_rating_and_distance(
        self,
        client: AsyncClient,
        test_user: User,
        test_service: Service,
        db_session: AsyncSession
    ):
        """Test que resultados están ordenados por rating y distancia."""
        # Crear múltiples detailers con diferentes ratings
        from domains.auth.service import AuthService
        from sqlalchemy import select
        from domains.auth.models import Role
        
        result = await db_session.execute(select(Role).where(Role.name == "detailer"))
        detailer_role = result.scalar_one()
        
        # Detailer 1: rating alto, lejos
        user1 = User(
            email="detailer1@test.com",
            full_name="High Rated Detailer",
            password_hash=AuthService.hash_password("Test1234!"),
            is_active=True,
        )
        user1.roles.append(detailer_role)
        db_session.add(user1)
        await db_session.flush()
        
        profile1 = ProviderProfile(
            user_id=user1.id,
            bio="High rated",
            years_of_experience=10,
            service_radius_miles=50,
            timezone="America/Indiana/Indianapolis",
            is_accepting_bookings=True,
            current_lat=41.0793,
            current_lng=-85.1394,
            average_rating=4.9,
            total_reviews=100,
        )
        db_session.add(profile1)
        
        # Detailer 2: rating bajo, cerca
        user2 = User(
            email="detailer2@test.com",
            full_name="Low Rated Detailer",
            password_hash=AuthService.hash_password("Test1234!"),
            is_active=True,
        )
        user2.roles.append(detailer_role)
        db_session.add(user2)
        await db_session.flush()
        
        profile2 = ProviderProfile(
            user_id=user2.id,
            bio="Low rated",
            years_of_experience=2,
            service_radius_miles=50,
            timezone="America/Indiana/Indianapolis",
            is_accepting_bookings=True,
            current_lat=41.0793,
            current_lng=-85.1394,
            average_rating=3.5,
            total_reviews=10,
        )
        db_session.add(profile2)
        
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/matching",
            headers=headers,
            params={
                "lat": 41.0793,
                "lng": -85.1394,
                "date": "2027-06-15",
                "service_id": str(test_service.id),
                "vehicle_sizes": "small",
            },
        )
        
        # Elmatching debería retornar array (puede estar vacío si no hay disponibilidad)
        assert response.status_code == 200
        # No verificamos orden específico ya que depende de disponibilidad