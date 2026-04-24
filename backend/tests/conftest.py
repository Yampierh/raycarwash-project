# backend/tests/conftest.py - Fixtures para pytest
import asyncio
import uuid
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from app.db.session import get_db
from app.models.models import Base, User, Role, UserRoleAssociation, ClientProfile, DetailerProfile
from app.core.config import get_settings
from app.core.limiter import limiter


# ============================================
# Rate limiter — disabled for all tests
# ============================================
@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable slowapi rate limiting for every test to prevent cross-test pollution."""
    limiter.enabled = False
    yield
    limiter.enabled = True


# ============================================
# Database fixtures - PostgreSQL
# ============================================
@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with PostgreSQL."""
    settings = get_settings()

    test_db_url = str(settings.DATABASE_URL)

    engine = create_async_engine(
        test_db_url,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        from app.db.seed_rbac import seed_rbac
        await seed_rbac(session)

        from app.db.seed import seed_services, seed_addons
        await seed_services(session)
        await seed_addons(session)

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_db: AsyncSession) -> AsyncSession:
    """Provide a clean database session for each test."""
    return test_db


# ============================================
# HTTP Client fixtures
# ============================================
@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def client_with_db(db_session: AsyncSession):
    """Client con override de DB."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, db_session

    app.dependency_overrides.clear()


# ============================================
# Auth fixtures
# ============================================

async def _create_user_with_role(
    db_session: AsyncSession,
    email: str,
    full_name: str,
    role_name: str,
    password: str = "Test1234!",
) -> User:
    """
    Helper that creates a fully-onboarded user with the given role.

    Uses UserRoleAssociation directly (not user.roles which is a read-only property).
    Sets onboarding_completed=True so the user can access protected endpoints.
    """
    from app.repositories.user_repository import UserRepository
    from app.services.auth import AuthService
    from sqlalchemy import select

    result = await db_session.execute(select(Role).where(Role.name == role_name))
    role = result.scalar_one()

    user = User(
        email=email,
        full_name=full_name,
        password_hash=AuthService.hash_password(password),
        is_active=True,
        onboarding_completed=True,
    )
    user_repo = UserRepository(db_session)
    created_user = await user_repo.create(user)
    await db_session.flush()

    db_session.add(UserRoleAssociation(user_id=created_user.id, role_id=role.id))

    if role_name == "client":
        db_session.add(ClientProfile(user_id=created_user.id))
    elif role_name == "detailer":
        db_session.add(DetailerProfile(user_id=created_user.id))

    await db_session.commit()

    await db_session.refresh(created_user, attribute_names=["user_roles"])
    for ur in created_user.user_roles:
        await db_session.refresh(ur, attribute_names=["role"])

    return created_user


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a fully-onboarded test user with client role."""
    return await _create_user_with_role(
        db_session,
        email="testclient@example.com",
        full_name="Test Client",
        role_name="client",
    )


@pytest.fixture
async def test_detailer(db_session: AsyncSession) -> User:
    """Create a fully-onboarded test user with detailer role."""
    return await _create_user_with_role(
        db_session,
        email="testdetailer@example.com",
        full_name="Test Detailer",
        role_name="detailer",
    )


@pytest.fixture
async def incomplete_user(db_session: AsyncSession) -> User:
    """
    User who registered but never completed onboarding.
    Has no role, no profile, onboarding_completed=False.
    """
    from app.repositories.user_repository import UserRepository
    from app.services.auth import AuthService

    user = User(
        email="incomplete@example.com",
        full_name=None,
        password_hash=AuthService.hash_password("Test1234!"),
        is_active=True,
        onboarding_completed=False,
    )
    user_repo = UserRepository(db_session)
    created = await user_repo.create(user)
    await db_session.commit()
    return created


# ============================================
# Token helpers
# ============================================

async def get_auth_tokens(client: AsyncClient, email: str, password: str) -> dict:
    """Helper function to get auth tokens via /auth/token (OAuth2 form)."""
    response = await client.post(
        "/auth/token",
        data={"username": email, "password": password},
    )
    if response.status_code == 200:
        return response.json()
    return None


async def get_access_token(client: AsyncClient, email: str, password: str = "Test1234!") -> str:
    """Shortcut: returns only the access token string."""
    tokens = await get_auth_tokens(client, email, password)
    return tokens["access_token"] if tokens else None


# ============================================
# Test data fixtures
# ============================================
@pytest.fixture
def sample_vehicle_data() -> dict:
    """Sample vehicle data for testing."""
    return {
        "make": "Toyota",
        "model": "Camry",
        "year": 2023,
        "license_plate": "ABC123",
        "color": "Silver",
        "body_class": "Sedan",
    }


@pytest.fixture
def sample_appointment_data() -> dict:
    """Sample appointment data for testing."""
    return {
        "detailer_id": str(uuid.uuid4()),
        "vehicle_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "scheduled_time": "2025-12-20T10:00:00Z",
        "service_address": "123 Test St",
        "service_latitude": 41.0793,
        "service_longitude": -85.1394,
    }


# ============================================
# Assertion helpers
# ============================================
def assert_valid_uuid(value: str, field_name: str = "id") -> None:
    """Assert that a value is a valid UUID."""
    import uuid as uuid_module
    try:
        uuid_module.UUID(value)
    except ValueError:
        pytest.fail(f"Expected valid UUID for {field_name}, got: {value}")


def assert_datetime_iso(value: str, field_name: str = "datetime") -> None:
    """Assert that a value is an ISO datetime string."""
    from datetime import datetime
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Expected ISO datetime for {field_name}, got: {value}")
