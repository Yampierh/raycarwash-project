from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import Role, UserRoleAssociation
from domains.onboarding.handlers.base import BaseOnboardingStep, TransitionResult
from domains.onboarding.models import OnboardingState
from domains.onboarding.state import OnboardingStep
from domains.providers.models import ProviderProfile, ProviderType
from domains.users.models import ClientProfile, User


VALID_SERVICE_TYPES: frozenset[str] = frozenset({"detailer"})
SERVICE_TYPE_TO_ROLE: dict[str, str] = {"detailer": "detailer"}
NEXT_STEP_MAP: dict[str, str] = {"client": "app", "detailer": "kyc"}


class AssignRoleStep(BaseOnboardingStep):

    @property
    def action_name(self) -> str:
        return "assign_role"

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
        if state.status != OnboardingStep.PROFILE_CREATION.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state for assign_role: {state.status}",
            )

    async def execute(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> TransitionResult:
        service_type = payload.get("service_type")
        if service_type and service_type.lower() not in VALID_SERVICE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid service_type. Valid: {sorted(VALID_SERVICE_TYPES)}",
            )

        if service_type:
            effective_role = SERVICE_TYPE_TO_ROLE[service_type.lower()]
        else:
            effective_role = "client"

        role_result = await db.execute(select(Role).where(Role.name == effective_role))
        role = role_result.scalar_one_or_none()

        if role:
            already_has_role = any(ur.role_id == role.id for ur in (user.user_roles or []))
            if not already_has_role:
                db.add(UserRoleAssociation(user_id=user.id, role_id=role.id))

        if effective_role == "client" and not user.client_profile:
            db.add(ClientProfile(user_id=user.id))
        elif effective_role == "detailer":
            existing = user.provider_profile_for(ProviderType.DETAILER)
            if not existing:
                db.add(
                    ProviderProfile(
                        user_id=user.id,
                        provider_type=ProviderType.DETAILER.value,
                    )
                )

        await db.flush()

        next_status = (
            OnboardingStep.KYC_PENDING.value
            if effective_role == "detailer"
            else OnboardingStep.COMPLETED.value
        )
        return TransitionResult(
            next_status=next_status,
            step="submit_kyc" if effective_role == "detailer" else None,
            metadata_updates={
                "assigned_role": effective_role,
                "_next_step": NEXT_STEP_MAP.get(effective_role, "app"),
            },
        )
