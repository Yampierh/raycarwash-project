from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.identity.service import IdentityService
from domains.onboarding.handlers.admin_kyc import AdminApproveKycStep, AdminRejectKycStep
from domains.onboarding.handlers.base import BaseOnboardingStep
from domains.onboarding.handlers.create_profile import CreateProfileStep
from domains.onboarding.handlers.assign_role import AssignRoleStep
from domains.onboarding.handlers.submit_kyc import SubmitKycStep
from domains.onboarding.models import OnboardingState
from domains.onboarding.state import OnboardingStep
from domains.onboarding.transitions import transition
from domains.users.models import User

logger = logging.getLogger(__name__)


class OnboardingOrchestrator:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        identity_svc = IdentityService(db)
        self._handlers: dict[str, BaseOnboardingStep] = {
            "create_profile": CreateProfileStep(),
            "assign_role": AssignRoleStep(),
            "submit_kyc": SubmitKycStep(),
            "approve_kyc": AdminApproveKycStep(identity_svc),
            "reject_kyc": AdminRejectKycStep(identity_svc),
        }

    async def advance(
        self,
        user: User,
        action: str,
        payload: dict[str, Any],
    ) -> OnboardingState:
        state = await self._get_state(user.id)
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Onboarding not started. Register first.",
            )
        return await self._apply_transition(user, state, action, payload)

    async def advance_system(
        self,
        target_user: User,
        action: str,
        payload: dict[str, Any],
    ) -> OnboardingState:
        """System-privileged transition bypassing JWT validation.

        Used by admin endpoints to approve/reject KYC for a target user.
        Same FSM engine as advance() but receives the user directly
        instead of extracting from the request token.
        """
        state = await self._get_state(target_user.id)
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Onboarding not started for target user.",
            )
        return await self._apply_transition(target_user, state, action, payload)

    async def _apply_transition(
        self,
        user: User,
        state: OnboardingState,
        action: str,
        payload: dict[str, Any],
    ) -> OnboardingState:
        handler = self._handlers.get(action)
        if handler is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action: {action}. "
                       f"Available: {list(self._handlers.keys())}",
            )

        await handler.validate(user, state, payload, self.db)

        result = await handler.execute(user, state, payload, self.db)

        from_step = OnboardingStep(state.status)
        to_step = OnboardingStep(result.next_status)
        transition(from_step, to_step)

        state.status = result.next_status
        state.current_step = result.step
        state.state_data.update(result.metadata_updates)

        if result.next_status == OnboardingStep.COMPLETED.value:
            state.completed = True
            user.onboarding_status = "completed"

        await self.db.flush()
        return state

    async def _get_state(self, user_id: Any) -> OnboardingState | None:
        stmt = select(OnboardingState).where(OnboardingState.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
