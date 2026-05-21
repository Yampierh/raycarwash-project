from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from domains.identity.service import IdentityService
from domains.onboarding.handlers.base import BaseOnboardingStep, TransitionResult
from domains.onboarding.models import OnboardingState
from domains.onboarding.state import OnboardingStep
from domains.users.models import User
from sqlalchemy.ext.asyncio import AsyncSession


class SubmitKycStep(BaseOnboardingStep):

    def __init__(self) -> None:
        self._identity_service: IdentityService | None = None

    def _get_identity_svc(self, db: AsyncSession) -> IdentityService:
        if self._identity_service is None:
            self._identity_service = IdentityService(db)
        return self._identity_service

    @property
    def action_name(self) -> str:
        return "submit_kyc"

    async def validate(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> None:
        if state.completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Onboarding already completed.",
            )
        if state.status not in (OnboardingStep.KYC_PENDING.value, OnboardingStep.KYC_REJECTED.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state for submit_kyc: {state.status}. "
                       f"Expected {OnboardingStep.KYC_PENDING.value} "
                       f"or {OnboardingStep.KYC_REJECTED.value}.",
            )
        document_data = payload.get("document_data", {})
        if not document_data.get("id_front_url") or not document_data.get("selfie_url"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Documentation incomplete. Both 'id_front_url' and 'selfie_url' are required.",
            )

    async def execute(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> TransitionResult:
        identity_svc = self._get_identity_svc(db)
        await identity_svc.submit_documents(
            user_id=user.id,
            document_data=payload.get("document_data", {}),
            verification_provider=payload.get("verification_provider"),
        )

        import datetime
        return TransitionResult(
            next_status=OnboardingStep.KYC_SUBMITTED.value,
            step=None,
            metadata_updates={
                "kyc_submission_date": str(datetime.datetime.now(datetime.timezone.utc)),
            },
        )
