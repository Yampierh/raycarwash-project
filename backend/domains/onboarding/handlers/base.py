from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from domains.onboarding.models import OnboardingState
from domains.users.models import User
from sqlalchemy.ext.asyncio import AsyncSession


class TransitionResult(BaseModel):
    next_status: str
    step: str | None = None
    metadata_updates: dict[str, Any] = {}


class BaseOnboardingStep(ABC):

    @property
    @abstractmethod
    def action_name(self) -> str:
        ...

    @abstractmethod
    async def validate(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> None:
        ...

    @abstractmethod
    async def execute(
        self,
        user: User,
        state: OnboardingState,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> TransitionResult:
        ...
