"""
test_admin_kyc.py

Admin KYC approval/rejection endpoints at POST /api/v1/admin/kyc/{user_id}/approve
and POST /api/v1/admin/kyc/{user_id}/reject.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.users.models import User, OnboardingStatus
from tests.conftest import _create_user_with_role, get_access_token


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _create_detailer_in_kyc_submitted(
    db_session: AsyncSession, email: str,
) -> uuid.UUID:
    """Create a detailer who has completed profile + submitted KYC docs."""
    from domains.auth.service import AuthService
    from domains.identity.models import IdentityVerification, KycStatus
    from domains.onboarding.models import OnboardingState
    from domains.onboarding.state import OnboardingStep as FsmStep
    from domains.users.repository import UserRepository

    user = User(
        email=email,
        full_name="KYC Pending Detailer",
        password_hash=AuthService.hash_password("Test1234!"),
        is_active=True,
        onboarding_status=OnboardingStatus.PENDING_PROFILE,
    )
    user = await UserRepository(db_session).create(user)
    await db_session.flush()

    from domains.auth.models import Role, UserRoleAssociation
    result = await db_session.execute(select(Role).where(Role.name == "detailer"))
    role = result.scalar_one()
    db_session.add(UserRoleAssociation(user_id=user.id, role_id=role.id))

    from domains.providers.models import ProviderProfile, ProviderType
    db_session.add(ProviderProfile(
        user_id=user.id,
        provider_type=ProviderType.DETAILER.value,
        bio="Test detailer",
        years_of_experience=3,
        service_radius_miles=25,
        timezone="America/Indiana/Indianapolis",
        is_accepting_bookings=False,
    ))

    onboarding_state = OnboardingState(
        user_id=user.id,
        status=FsmStep.KYC_SUBMITTED.value,
        current_step=None,
        completed=False,
    )
    db_session.add(onboarding_state)

    identity = IdentityVerification(
        user_id=user.id,
        status=KycStatus.SUBMITTED.value,
        document_data={"id_front_url": "https://s3.example.com/id.jpg", "selfie_url": "https://s3.example.com/selfie.jpg"},
    )
    db_session.add(identity)

    await db_session.commit()
    return user.id


async def _admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    await _create_user_with_role(db_session, "admin@test.com", "Admin", "admin")
    token = await get_access_token(client, "admin@test.com")
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Auth guards
# ─────────────────────────────────────────────────────────────────────────────

class TestKycAuthGuards:

    @pytest.mark.asyncio
    async def test_approve_requires_auth(self, client: AsyncClient):
        resp = await client.post(f"/api/v1/admin/kyc/{uuid.uuid4()}/approve")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_approve_requires_admin_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "regular@test.com", "Regular", "client")
        token = await get_access_token(client, "regular@test.com")
        resp = await client.post(
            f"/api/v1/admin/kyc/{uuid.uuid4()}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_reject_requires_auth(self, client: AsyncClient):
        resp = await client.post(f"/api/v1/admin/kyc/{uuid.uuid4()}/reject")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_reject_requires_admin_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "regular2@test.com", "Regular", "client")
        token = await get_access_token(client, "regular2@test.com")
        resp = await client.post(
            f"/api/v1/admin/kyc/{uuid.uuid4()}/reject",
            json={"reason": "Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Approve KYC
# ─────────────────────────────────────────────────────────────────────────────

class TestKycApprove:

    @pytest.mark.asyncio
    async def test_approve_transitions_to_completed(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_id = await _create_detailer_in_kyc_submitted(db_session, "kyc-approve@test.com")
        headers = await _admin_headers(client, db_session)

        resp = await client.post(
            f"/api/v1/admin/kyc/{user_id}/approve",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["completed"] is True
        assert data["message"] == "KYC approved."

        from domains.onboarding.models import OnboardingState
        stmt = select(OnboardingState).where(OnboardingState.user_id == user_id)
        result = await db_session.execute(stmt)
        state = result.scalar_one()
        assert state.status == "completed"
        assert state.completed is True

        from domains.identity.models import IdentityVerification, KycStatus
        stmt = select(IdentityVerification).where(IdentityVerification.user_id == user_id)
        result = await db_session.execute(stmt)
        identity = result.scalar_one()
        assert identity.status == KycStatus.APPROVED.value

        user = await db_session.get(User, user_id)
        assert user.onboarding_completed is True

    @pytest.mark.asyncio
    async def test_approve_nonexistent_user_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        fake_id = uuid.uuid4()
        resp = await client.post(
            f"/api/v1/admin/kyc/{fake_id}/approve",
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_invalid_uuid_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            "/api/v1/admin/kyc/not-a-uuid/approve",
            headers=headers,
        )
        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Reject KYC
# ─────────────────────────────────────────────────────────────────────────────

class TestKycReject:

    @pytest.mark.asyncio
    async def test_reject_transitions_to_kyc_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_id = await _create_detailer_in_kyc_submitted(db_session, "kyc-reject@test.com")
        headers = await _admin_headers(client, db_session)

        resp = await client.post(
            f"/api/v1/admin/kyc/{user_id}/reject",
            json={"reason": "Documentation does not match identity."},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "kyc_rejected"
        assert data["completed"] is False
        assert data["current_step"] == "submit_kyc"

        from domains.identity.models import IdentityVerification, KycStatus
        stmt = select(IdentityVerification).where(IdentityVerification.user_id == user_id)
        result = await db_session.execute(stmt)
        identity = result.scalar_one()
        assert identity.status == KycStatus.REJECTED.value
        assert identity.rejection_reason == "Documentation does not match identity."

    @pytest.mark.asyncio
    async def test_reject_nonexistent_user_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        fake_id = uuid.uuid4()
        resp = await client.post(
            f"/api/v1/admin/kyc/{fake_id}/reject",
            json={"reason": "Test"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_invalid_uuid_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            "/api/v1/admin/kyc/not-a-uuid/reject",
            json={"reason": "Test"},
            headers=headers,
        )
        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# FSM guard — only KYC_SUBMITTED can be approved/rejected
# ─────────────────────────────────────────────────────────────────────────────

class TestKycFsmGuards:

    @pytest.mark.asyncio
    async def test_approve_wrong_state_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        from domains.auth.service import AuthService
        from domains.onboarding.models import OnboardingState
        from domains.onboarding.state import OnboardingStep as FsmStep
        from domains.users.repository import UserRepository

        user = User(
            email="kyc-pending@test.com",
            full_name="KYC Pending",
            password_hash=AuthService.hash_password("Test1234!"),
            is_active=True,
            onboarding_status=OnboardingStatus.PENDING_PROFILE,
        )
        user = await UserRepository(db_session).create(user)
        db_session.add(OnboardingState(
            user_id=user.id,
            status=FsmStep.KYC_PENDING.value,
            current_step="submit_kyc",
            completed=False,
        ))
        await db_session.commit()

        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            f"/api/v1/admin/kyc/{user.id}/approve",
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reject_wrong_state_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        from domains.auth.service import AuthService
        from domains.onboarding.models import OnboardingState
        from domains.onboarding.state import OnboardingStep as FsmStep
        from domains.users.repository import UserRepository

        user = User(
            email="kyc-pending2@test.com",
            full_name="KYC Pending 2",
            password_hash=AuthService.hash_password("Test1234!"),
            is_active=True,
            onboarding_status=OnboardingStatus.PENDING_PROFILE,
        )
        user = await UserRepository(db_session).create(user)
        db_session.add(OnboardingState(
            user_id=user.id,
            status=FsmStep.KYC_PENDING.value,
            current_step="submit_kyc",
            completed=False,
        ))
        await db_session.commit()

        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            f"/api/v1/admin/kyc/{user.id}/reject",
            json={"reason": "Test"},
            headers=headers,
        )
        assert resp.status_code == 400
