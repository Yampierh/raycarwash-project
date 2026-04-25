# backend/tests/test_appointments.py - Tests de citas/turnos
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import User, Vehicle, Service, Appointment, AppointmentStatus


# ============================================
# Fixtures helper
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
async def test_service(db_session: AsyncSession) -> Service:
    """Create a test service."""
    service = Service(
        name="Exterior Wash",
        description="Basic exterior wash",
        base_price_cents=2900,  # $29.00
        base_duration_minutes=45,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)
    return service


@pytest.fixture
async def test_vehicle(db_session: AsyncSession, test_user: User) -> Vehicle:
    """Create a test vehicle."""
    vehicle = Vehicle(
        owner_id=test_user.id,
        make="Toyota",
        model="Camry",
        year=2023,
        license_plate="VEH123",
        color="Silver",
    )
    db_session.add(vehicle)
    await db_session.commit()
    await db_session.refresh(vehicle)
    return vehicle


@pytest.fixture
async def test_appointment(
    db_session: AsyncSession,
    test_user: User,
    test_detailer: User,
    test_service: Service,
    test_vehicle: Vehicle
) -> Appointment:
    """Create a test appointment in PENDING status."""
    from app.models.models import ProviderProfile, AppointmentVehicle
    
    # Create detailer profile
    provider_profile = ProviderProfile(
        user_id=test_detailer.id,
        bio="Test detailer",
        years_of_experience=5,
        service_radius_miles=25,
        timezone="America/Indiana/Indianapolis",
        is_accepting_bookings=True,
    )
    db_session.add(provider_profile)
    await db_session.flush()
    
    # Create appointment
    appointment = Appointment(
        client_id=test_user.id,
        detailer_id=test_detailer.id,
        service_id=test_service.id,
        vehicle_id=test_vehicle.id,
        scheduled_time="2025-12-20T10:00:00Z",
        service_address="123 Test St",
        service_latitude=41.0793,
        service_longitude=-85.1394,
        estimated_price=2900,
        status=AppointmentStatus.PENDING,
    )
    db_session.add(appointment)
    await db_session.flush()
    
    # Add appointment vehicle
    appt_vehicle = AppointmentVehicle(
        appointment_id=appointment.id,
        vehicle_id=test_vehicle.id,
        vehicle_size="medium",
        price_cents=2900,
        duration_minutes=45,
    )
    db_session.add(appt_vehicle)
    
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


# ============================================
# Tests: POST /api/v1/appointments (Create Appointment)
# ============================================
class TestCreateAppointment:
    """Tests para crear citas."""
    
    @pytest.mark.asyncio
    async def test_create_appointment_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_detailer: User,
        test_service: Service,
        test_vehicle: Vehicle,
        db_session: AsyncSession
    ):
        """Test crear cita exitosamente."""
        # Setup detailer profile
        from app.models.models import ProviderProfile
        profile = ProviderProfile(
            user_id=test_detailer.id,
            bio="Test",
            years_of_experience=5,
            service_radius_miles=25,
            timezone="America/Indiana/Indianapolis",
            is_accepting_bookings=True,
        )
        db_session.add(profile)
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.post(
            "/api/v1/appointments",
            headers=headers,
            json={
                "detailer_id": str(test_detailer.id),
                "vehicle_id": str(test_vehicle.id),
                "service_id": str(test_service.id),
                "scheduled_time": "2025-12-20T14:00:00Z",
                "service_address": "123 Test Street",
                "service_latitude": 41.0793,
                "service_longitude": -85.1394,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert "estimated_price" in data
    
    @pytest.mark.asyncio
    async def test_create_appointment_unauthenticated(self, client: AsyncClient):
        """Test crear cita sin autenticación."""
        response = await client.post(
            "/api/v1/appointments",
            json={
                "detailer_id": str(uuid.uuid4()),
                "vehicle_id": str(uuid.uuid4()),
                "service_id": str(uuid.uuid4()),
                "scheduled_time": "2025-12-20T10:00:00Z",
                "service_address": "Test St",
                "service_latitude": 41.0793,
                "service_longitude": -85.1394,
            },
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_appointment_nonexistent_detailer(
        self,
        client: AsyncClient,
        test_user: User,
        test_vehicle: Vehicle,
        test_service: Service
    ):
        """Test crear cita con detailer que no existe."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.post(
            "/api/v1/appointments",
            headers=headers,
            json={
                "detailer_id": str(uuid.uuid4()),
                "vehicle_id": str(test_vehicle.id),
                "service_id": str(test_service.id),
                "scheduled_time": "2025-12-20T10:00:00Z",
                "service_address": "Test St",
                "service_latitude": 41.0793,
                "service_longitude": -85.1394,
            },
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_appointment_vehicle_not_owned(
        self,
        client: AsyncClient,
        test_user: User,
        test_detailer: User,
        test_service: Service,
        db_session: AsyncSession
    ):
        """Test crear cita con vehículo que no pertenece al usuario."""
        # Create another user's vehicle
        other_user = User(
            email="other@example.com",
            full_name="Other User",
            password_hash="dummy",
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.flush()
        
        other_vehicle = Vehicle(
            owner_id=other_user.id,
            make="Honda",
            model="Civic",
            year=2022,
            license_plate="OTHER",
            color="Blue",
        )
        db_session.add(other_vehicle)
        await db_session.commit()
        await db_session.refresh(other_vehicle)
        
        # Setup detailer profile
        from app.models.models import ProviderProfile
        profile = ProviderProfile(
            user_id=test_detailer.id,
            bio="Test",
            years_of_experience=5,
            service_radius_miles=25,
            timezone="America/Indiana/Indianapolis",
            is_accepting_bookings=True,
        )
        db_session.add(profile)
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.post(
            "/api/v1/appointments",
            headers=headers,
            json={
                "detailer_id": str(test_detailer.id),
                "vehicle_id": str(other_vehicle.id),
                "service_id": str(test_service.id),
                "scheduled_time": "2025-12-20T10:00:00Z",
                "service_address": "Test St",
                "service_latitude": 41.0793,
                "service_longitude": -85.1394,
            },
        )
        
        assert response.status_code == 422


# ============================================
# Tests: GET /api/v1/appointments/mine (List Appointments)
# ============================================
class TestListAppointments:
    """Tests para listar citas."""
    
    @pytest.mark.asyncio
    async def test_list_appointments_empty(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test listar citas cuando no hay ninguna."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/appointments/mine",
            headers=headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_list_appointments_pagination(
        self,
        client: AsyncClient,
        test_user: User,
        test_appointment: Appointment
    ):
        """Test paginación de citas."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/appointments/mine?page=1&page_size=10",
            headers=headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["page"] == 1
        assert data["page_size"] == 10
    
    @pytest.mark.asyncio
    async def test_list_appointments_detailer(
        self,
        client: AsyncClient,
        test_detailer: User,
        test_appointment: Appointment
    ):
        """Test que detailer ve sus propias citas."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.get(
            "/api/v1/appointments/mine",
            headers=headers,
        )
        
        assert response.status_code == 200


# ============================================
# Tests: GET /api/v1/appointments/{id} (Get Appointment)
# ============================================
class TestGetAppointment:
    """Tests para obtener una cita específica."""
    
    @pytest.mark.asyncio
    async def test_get_appointment_as_client(
        self,
        client: AsyncClient,
        test_user: User,
        test_appointment: Appointment
    ):
        """Test cliente obtiene su propia cita."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.get(
            f"/api/v1/appointments/{test_appointment.id}",
            headers=headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_appointment.id)
    
    @pytest.mark.asyncio
    async def test_get_appointment_as_detailer(
        self,
        client: AsyncClient,
        test_detailer: User,
        test_appointment: Appointment
    ):
        """Test detailer obtiene la cita asignada."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.get(
            f"/api/v1/appointments/{test_appointment.id}",
            headers=headers,
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_appointment_not_participant(
        self,
        client: AsyncClient,
        test_detailer: User,
        test_appointment: Appointment,
        db_session: AsyncSession
    ):
        """Test usuario no participante no puede ver la cita."""
        # Create third user
        from app.services.auth import AuthService
        other_user = User(
            email="other@example.com",
            full_name="Other User",
            password_hash=AuthService.hash_password("Test1234!"),
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "other@example.com", "Test1234!"
        )
        
        response = await client.get(
            f"/api/v1/appointments/{test_appointment.id}",
            headers=headers,
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_appointment(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test obtener cita que no existe."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/v1/appointments/{fake_uuid}",
            headers=headers,
        )
        
        assert response.status_code == 404


# ============================================
# Tests: PATCH /api/v1/appointments/{id}/status (State Machine)
# ============================================
class TestAppointmentStatus:
    """Tests para el state machine de citas."""
    
    @pytest.mark.asyncio
    async def test_status_pending_to_confirmed(
        self,
        client: AsyncClient,
        test_detailer: User,
        test_appointment: Appointment
    ):
        """Test detailer confirma cita pending."""
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.patch(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=headers,
            json={"status": "confirmed"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"
    
    @pytest.mark.asyncio
    async def test_status_confirmed_to_in_progress(
        self,
        client: AsyncClient,
        test_detailer: User,
        test_appointment: Appointment,
        db_session: AsyncSession
    ):
        """Test detailer inicia cita confirmada."""
        # First confirm
        test_appointment.status = AppointmentStatus.CONFIRMED
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.patch(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=headers,
            json={"status": "in_progress"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["started_at"] is not None
    
    @pytest.mark.asyncio
    async def test_status_in_progress_to_completed(
        self,
        client: AsyncClient,
        test_detailer: User,
        test_appointment: Appointment,
        db_session: AsyncSession
    ):
        """Test detailer completa cita en progreso."""
        # Set to in_progress
        test_appointment.status = AppointmentStatus.IN_PROGRESS
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.patch(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=headers,
            json={
                "status": "completed",
                "actual_price": 3500,  # $35.00
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["actual_price"] == 3500
        assert data["completed_at"] is not None
    
    @pytest.mark.asyncio
    async def test_status_completed_requires_actual_price(
        self,
        client: AsyncClient,
        test_detailer: User,
        test_appointment: Appointment,
        db_session: AsyncSession
    ):
        """Test que completar requiere actual_price."""
        test_appointment.status = AppointmentStatus.IN_PROGRESS
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.patch(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=headers,
            json={"status": "completed"},  # Sin actual_price
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_status_cancel_by_client(
        self,
        client: AsyncClient,
        test_user: User,
        test_appointment: Appointment
    ):
        """Test cliente cancela cita pending."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.patch(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=headers,
            json={"status": "cancelled_by_client"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled_by_client"
    
    @pytest.mark.asyncio
    async def test_status_invalid_transition(
        self,
        client: AsyncClient,
        test_user: User,
        test_appointment: Appointment
    ):
        """Test transición inválida (pending -> completed)."""
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.patch(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=headers,
            json={"status": "completed", "actual_price": 2900},
        )
        
        # Cliente no puede مباشرة ir a completed
        assert response.status_code in [403, 422]
    
    @pytest.mark.asyncio
    async def test_status_cannot_change_completed(
        self,
        client: AsyncClient,
        test_detailer: User,
        test_appointment: Appointment,
        db_session: AsyncSession
    ):
        """Test que no se puede cambiar estado de cita completada."""
        test_appointment.status = AppointmentStatus.COMPLETED
        test_appointment.actual_price = 2900
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "testdetailer@example.com", "Test1234!"
        )
        
        response = await client.patch(
            f"/api/v1/appointments/{test_appointment.id}/status",
            headers=headers,
            json={"status": "cancelled_by_client"},
        )
        
        # Terminal states shouldn't have outgoing transitions
        assert response.status_code in [409, 422]


# ============================================
# Tests: Multi-vehicle appointments (Sprint 5)
# ============================================
class TestMultiVehicleAppointment:
    """Tests para citas multi-vehículo."""
    
    @pytest.mark.asyncio
    async def test_create_multi_vehicle_appointment(
        self,
        client: AsyncClient,
        test_user: User,
        test_detailer: User,
        test_service: Service,
        test_vehicle: Vehicle,
        db_session: AsyncSession
    ):
        """Test crear cita con múltiples vehículos."""
        # Setup detailer profile
        from app.models.models import ProviderProfile
        profile = ProviderProfile(
            user_id=test_detailer.id,
            bio="Test",
            years_of_experience=5,
            service_radius_miles=25,
            timezone="America/Indiana_Indianapolis",
            is_accepting_bookings=True,
        )
        db_session.add(profile)
        
        # Create second vehicle
        vehicle2 = Vehicle(
            owner_id=test_user.id,
            make="Honda",
            model="Civic",
            year=2022,
            license_plate="VEH2",
            color="Red",
        )
        db_session.add(vehicle2)
        await db_session.commit()
        
        headers = await get_auth_headers(
            client, "testclient@example.com", "Test1234!"
        )
        
        response = await client.post(
            "/api/v1/appointments",
            headers=headers,
            json={
                "detailer_id": str(test_detailer.id),
                "scheduled_time": "2025-12-20T14:00:00Z",
                "service_address": "123 Test Street",
                "service_latitude": 41.0793,
                "service_longitude": -85.1394,
                "vehicles": [
                    {
                        "vehicle_id": str(test_vehicle.id),
                        "service_id": str(test_service.id),
                    },
                    {
                        "vehicle_id": str(vehicle2.id),
                        "service_id": str(test_service.id),
                    },
                ],
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data.get("vehicles", [])) >= 1