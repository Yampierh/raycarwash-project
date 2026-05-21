from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from domains.onboarding.handlers.base import BaseOnboardingStep, TransitionResult
from domains.onboarding.models import OnboardingState
from domains.onboarding.state import OnboardingStep
from domains.users.models import User
from sqlalchemy.ext.asyncio import AsyncSession


class CreateProfileStep(BaseOnboardingStep):

    @property
    def action_name(self) -> str:
        return "create_profile"

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
        if state.status != OnboardingStep.PENDING_REGISTRATION.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state for create_profile: {state.status}",
            )
        if not payload.get("full_name"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="full_name is required.",
            )

    async def execute(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> TransitionResult:
        user.full_name = payload["full_name"]
        if payload.get("phone_number"):
            user.phone_number = payload["phone_number"]

        updates: dict[str, Any] = {
            "full_name": payload["full_name"],
        }
        if payload.get("phone_number"):
            updates["phone_number"] = payload["phone_number"]

        return TransitionResult(
            next_status=OnboardingStep.PROFILE_CREATION.value,
            step="assign_role",
            metadata_updates=updates,
        )
