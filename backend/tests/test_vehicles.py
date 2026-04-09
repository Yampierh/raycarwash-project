# backend/tests/test_vehicles.py - Tests de vehículos
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import User, Vehicle, Role


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


async def create_test_user_with_session(db_session: AsyncSession) -> User:
    """Create a test user with client role using the provided session."""
    from app.services.auth import AuthService
    from sqlalchemy import select
    
    result = await db_session.execute(select(Role).where(Role.name == "client"))
    client_role = result.scalar_one()
    
    user = User(
        email="testclient@example.com",
        full_name="Test Client",
        password_hash=AuthService.hash_password("Test1234!"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create user role association
    from app.models.models import UserRoleAssociation
    user_role = UserRoleAssociation(user_id=user.id, role_id=client_role.id)
    db_session.add(user_role)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Verify roles are set correctly
    await db_session.refresh(user, attribute_names=['user_roles'])
    for ur in user.user_roles:
        await db_session.refresh(ur, attribute_names=['role'])
    
    return user


# ============================================
# Tests: POST /api/v1/vehicles (Create Vehicle)
# ============================================
class TestCreateVehicle:
    """Tests para crear vehículos."""
    
    @pytest.mark.asyncio
    async def test_create_vehicle_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test crear vehículo exitosamente."""
        # Create user with same session
        test_user = await create_test_user_with_session(db_session)
        
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.post(
            "/api/v1/vehicles",
            headers=headers,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "ABC123",
                "color": "Silver",
                "body_class": "Sedan",
            },
        )
        
        assert response.status_code == 201, f"Response: {response.status_code} - {response.text}"
        data = response.json()
        assert data["make"] == "Toyota"
        assert data["model"] == "Camry"
        assert data["year"] == 2023
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_vehicle_unauthenticated(self, client: AsyncClient):
        """Test crear vehículo sin autenticación."""
        response = await client.post(
            "/api/v1/vehicles",
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "ABC123",
            },
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_vehicle_detailer_forbidden(self, client: AsyncClient, test_detailer: User):
        """Test que detailer no puede crear vehículos."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.post(
            "/api/v1/vehicles",
            headers=headers,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "XYZ789",
                "color": "Blue",
            },
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_create_vehicle_duplicate_plate(self, client: AsyncClient, test_user: User):
        """Test crear vehículo con placa duplicada."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        # Crear primer vehículo
        await client.post(
            "/api/v1/vehicles",
            headers=headers,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "DUPLICATE",
                "color": "Silver",
            },
        )
        
        # Intentar crear segundo con misma placa
        response = await client.post(
            "/api/v1/vehicles",
            headers=headers,
            json={
                "make": "Honda",
                "model": "Civic",
                "year": 2022,
                "license_plate": "DUPLICATE",
                "color": "Red",
            },
        )
        
        assert response.status_code == 409
    
    @pytest.mark.asyncio
    async def test_create_vehicle_invalid_year(self, client: AsyncClient, test_user: User):
        """Test crear vehículo con año inválido."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.post(
            "/api/v1/vehicles",
            headers=headers,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 1800,  # Año inválido
                "license_plate": "TEST123",
                "color": "Silver",
            },
        )
        
        assert response.status_code == 422


# ============================================
# Tests: GET /api/v1/vehicles (List Vehicles)
# ============================================
class TestListVehicles:
    """Tests para listar vehículos."""
    
    @pytest.mark.asyncio
    async def test_list_vehicles_empty(self, client: AsyncClient, test_user: User):
        """Test listar vehículos cuando no hay ninguno."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/vehicles",
            headers=headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    @pytest.mark.asyncio
    async def test_list_vehicles_with_data(self, client: AsyncClient, test_user: User):
        """Test listar vehículos con datos."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        # Crear algunos vehículos primero
        await client.post(
            "/api/v1/vehicles",
            headers=headers,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "VEH1",
                "color": "Silver",
            },
        )
        await client.post(
            "/api/v1/vehicles",
            headers=headers,
            json={
                "make": "Honda",
                "model": "Civic",
                "year": 2022,
                "license_plate": "VEH2",
                "color": "Red",
            },
        )
        
        response = await client.get(
            "/api/v1/vehicles",
            headers=headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    @pytest.mark.asyncio
    async def test_list_vehicles_unauthenticated(self, client: AsyncClient):
        """Test listar vehículos sin autenticación."""
        response = await client.get("/api/v1/vehicles")
        
        assert response.status_code == 401


# ============================================
# Tests: GET /api/v1/vehicles/lookup/{vin} (VIN Lookup)
# ============================================
class TestVinLookup:
    """Tests para lookup de VIN."""
    
    @pytest.mark.asyncio
    async def test_vin_lookup_valid(self, client: AsyncClient, test_user: User):
        """Test lookup de VIN válido (17 caracteres)."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/vehicles/lookup/1HGBH41JXMN109186",
            headers=headers,
        )
        
        # Puede ser 200 (datos encontrados) o 404 (no encontrado en NHTSA)
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_vin_lookup_invalid_short(self, client: AsyncClient, test_user: User):
        """Test lookup con VIN muy corto."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/vehicles/lookup/ABC",
            headers=headers,
        )
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_vin_lookup_unauthenticated(self, client: AsyncClient):
        """Test lookup sin autenticación."""
        response = await client.get(
            "/api/v1/vehicles/lookup/1HGBH41JXMN109186",
        )
        
        assert response.status_code == 401


# ============================================
# Tests: DELETE /api/v1/vehicles/{id} (Delete Vehicle)
# ============================================
class TestDeleteVehicle:
    """Tests para eliminar vehículos (soft delete)."""
    
    @pytest.mark.asyncio
    async def test_delete_vehicle_success(self, client: AsyncClient, test_user: User):
        """Test eliminar vehículo exitosamente."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        # Crear vehículo primero
        create_response = await client.post(
            "/api/v1/vehicles",
            headers=headers,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "DEL123",
                "color": "Silver",
            },
        )
        vehicle_id = create_response.json()["id"]
        
        # Eliminar
        response = await client.delete(
            f"/api/v1/vehicles/{vehicle_id}",
            headers=headers,
        )
        
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_delete_vehicle_not_owner(self, client: AsyncClient, test_user: User, test_detailer: User):
        """Test eliminar vehículo de otro usuario."""
        # Crear vehículo con test_user
        headers_user = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        create_response = await client.post(
            "/api/v1/vehicles",
            headers=headers_user,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "OWNER123",
                "color": "Silver",
            },
        )
        vehicle_id = create_response.json()["id"]
        
        # Intentar eliminar con detailer
        headers_detailer = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        response = await client.delete(
            f"/api/v1/vehicles/{vehicle_id}",
            headers=headers_detailer,
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_vehicle(self, client: AsyncClient, test_user: User):
        """Test eliminar vehículo que no existe."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(
            f"/api/v1/vehicles/{fake_uuid}",
            headers=headers,
        )
        
        assert response.status_code == 404


# ============================================
# Tests: PUT /api/v1/vehicles/{id} (Update Vehicle)
# ============================================
class TestUpdateVehicle:
    """Tests para actualizar vehículos."""
    
    @pytest.mark.asyncio
    async def test_update_vehicle_success(self, client: AsyncClient, test_user: User):
        """Test actualizar vehículo exitosamente."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        # Crear vehículo
        create_response = await client.post(
            "/api/v1/vehicles",
            headers=headers,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "UPD123",
                "color": "Silver",
            },
        )
        vehicle_id = create_response.json()["id"]
        
        # Actualizar
        response = await client.put(
            f"/api/v1/vehicles/{vehicle_id}",
            headers=headers,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2024,
                "license_plate": "UPD123",
                "color": "Gold",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["color"] == "Gold"
        assert data["year"] == 2024
    
    @pytest.mark.asyncio
    async def test_update_vehicle_not_owner(self, client: AsyncClient, test_user: User, test_detailer: User):
        """Test actualizar vehículo de otro usuario."""
        headers_user = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        create_response = await client.post(
            "/api/v1/vehicles",
            headers=headers_user,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "NOTOWNER",
                "color": "Silver",
            },
        )
        vehicle_id = create_response.json()["id"]
        
        headers_detailer = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        response = await client.put(
            f"/api/v1/vehicles/{vehicle_id}",
            headers=headers_detailer,
            json={
                "make": "Honda",
                "model": "Civic",
                "year": 2023,
                "license_plate": "NOTOWNER",
                "color": "Red",
            },
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_vehicle(self, client: AsyncClient, test_user: User):
        """Test actualizar vehículo que no existe."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.put(
            f"/api/v1/vehicles/{fake_uuid}",
            headers=headers,
            json={
                "make": "Toyota",
                "model": "Camry",
                "year": 2023,
                "license_plate": "TEST",
                "color": "Silver",
            },
        )
        
        assert response.status_code == 404