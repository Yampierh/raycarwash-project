from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from domains.users.models import OnboardingStatus, User
from domains.users.repository import UserRepository


class UserService:

    def __init__(self, db: AsyncSession) -> None:
        self._repo = UserRepository(db)

    async def create_user(self, email: str, password_hash: str) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            onboarding_status=OnboardingStatus.PENDING_PROFILE,
        )
        return await self._repo.create(user)
