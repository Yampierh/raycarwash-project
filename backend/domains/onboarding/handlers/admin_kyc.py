from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from domains.identity.service import IdentityService
from domains.onboarding.handlers.base import BaseOnboardingStep, TransitionResult
from domains.onboarding.models import OnboardingState
from domains.onboarding.state import OnboardingStep
from domains.users.models import User
from sqlalchemy.ext.asyncio import AsyncSession


class AdminApproveKycStep(BaseOnboardingStep):

    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity_service = identity_service

    def _get_identity_svc(self, db: AsyncSession) -> IdentityService:
        if self._identity_service is None:
            self._identity_service = IdentityService(db)
        return self._identity_service

    @property
    def action_name(self) -> str:
        return "approve_kyc"

    async def validate(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> None:
        if state.status != OnboardingStep.KYC_SUBMITTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User is not in KYC review. Status: {state.status}",
            )

    async def execute(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> TransitionResult:
        identity_svc = self._get_identity_svc(db)
        await identity_svc.approve_kyc(user.id)

        return TransitionResult(
            next_status=OnboardingStep.COMPLETED.value,
            step=None,
            metadata_updates={
                "kyc_approved_by": payload.get("admin_id"),
                "kyc_approved_at": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc,
                ).isoformat(),
            },
        )


class AdminRejectKycStep(BaseOnboardingStep):

    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity_service = identity_service

    def _get_identity_svc(self, db: AsyncSession) -> IdentityService:
        if self._identity_service is None:
            self._identity_service = IdentityService(db)
        return self._identity_service

    @property
    def action_name(self) -> str:
        return "reject_kyc"

    async def validate(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> None:
        if state.status != OnboardingStep.KYC_SUBMITTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User is not in KYC review. Status: {state.status}",
            )

    async def execute(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> TransitionResult:
        reason = payload.get("reason", "Does not meet minimum requirements.")
        identity_svc = self._get_identity_svc(db)
        await identity_svc.reject_kyc(user.id, reason)

        return TransitionResult(
            next_status=OnboardingStep.KYC_REJECTED.value,
            step="submit_kyc",
            metadata_updates={
                "kyc_rejected_by": payload.get("admin_id"),
                "kyc_rejected_reason": reason,
            },
        )
