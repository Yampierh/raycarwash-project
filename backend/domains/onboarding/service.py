from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.onboarding.models import OnboardingState
from domains.onboarding.state import INITIAL_STEP
from domains.users.models import User


class OnboardingService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def start(self, user: User, intent_role: str | None = None) -> OnboardingState:
        state = OnboardingState(
            user_id=user.id,
            status=INITIAL_STEP.value,
            current_step="create_profile",
            metadata={},
            completed=False,
        )
        if intent_role:
            state.state_data["intent_role"] = intent_role
        self.db.add(state)
        await self.db.flush()
        return state

    async def get_state(self, user_id) -> OnboardingState | None:
        stmt = select(OnboardingState).where(OnboardingState.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
