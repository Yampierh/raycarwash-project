# app/repositories/user_repository.py
#
# WHY a Repository layer?
# The Repository pattern encapsulates all raw DB queries, giving services
# a clean, mockable interface. This means:
#  1. Services contain ONLY business logic — no SQLAlchemy constructs.
#  2. Unit tests can swap the repository for an in-memory fake without
#     spinning up a database.
#  3. If we later move to a different ORM or add a Redis cache, only
#     the repository changes — zero impact on the service layer.

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import Role, UserRoleAssociation
from domains.users.models import User


class UserRepository:
    """
    All database operations for the `users` table.

    Never instantiated as a singleton — one instance per request,
    sharing the request-scoped AsyncSession injected via Depends(get_db).
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """
        Fetch an active (non-deleted) user by primary key.

        Returns None if the user does not exist or has been soft-deleted.
        The service layer is responsible for raising a 404 if None is returned.
        """
        stmt = select(User).where(
            User.id == user_id,
            User.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Fetch an active user by email address (case-insensitive).

        Used by AuthService.authenticate_user() during login.
        The `lower()` normalisation is intentional — emails are stored
        lowercase (enforced by UserCreate validator), but we lower() the
        lookup value too as a defensive measure.
        """
        stmt = (
            select(User)
            .where(
                User.email == email.lower(),
                User.is_deleted.is_(False),
            )
            .options(
                selectinload(User.user_roles).selectinload(UserRoleAssociation.role)
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_detailer(self, detailer_id: uuid.UUID) -> User | None:
        """
        Fetch an active (non-deleted) user with the 'detailer' role.

        Used by AppointmentService to validate the chosen detailer before
        creating a booking. A regular CLIENT id must not be bookable.
        """
        stmt = (
            select(User)
            .join(UserRoleAssociation, UserRoleAssociation.user_id == User.id)
            .join(Role, Role.id == UserRoleAssociation.role_id)
            .where(
                User.id == detailer_id,
                Role.name == "detailer",
                User.is_active.is_(True),
                User.is_deleted.is_(False),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """
        Persist a new User and flush to obtain the database-generated PK.

        `flush()` sends the INSERT to PostgreSQL within the current
        transaction but does NOT commit. The commit happens in `get_db()`
        after the handler returns successfully, keeping the transaction
        boundary at the request level.
        """
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def update(self, user: User, fields: dict) -> User:
        """Apply a dict of field updates to the user and flush."""
        from datetime import datetime, timezone
        fields["updated_at"] = datetime.now(timezone.utc)
        for key, value in fields.items():
            setattr(user, key, value)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def email_exists(self, email: str) -> bool:
        """
        Lightweight uniqueness check before attempting an INSERT.

        Avoids relying solely on the DB unique-constraint exception for
        a cleaner 409 response with a descriptive message. The constraint
        still exists as the authoritative guard.
        """
        stmt = select(User.id).where(
            User.email == email.lower(),
            User.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_phone(self, phone: str) -> User | None:
        """
        Fetch an active user by phone number using phone_hash index.
        
        FIX: Now uses the phone_hash column for O(1) lookup.
        - Computes HMAC-SHA256 hash of the phone number
        - Queries using the hash (indexed, unique)
        - Returns user if found and active
        """
        from app.core.config import get_settings
        from app.core.security import compute_phone_hash
        
        settings = get_settings()
        
        # Compute hash using the lookup key
        phone_hash = compute_phone_hash(phone, settings.PHONE_LOOKUP_KEY)
        
        stmt = select(User).where(
            User.phone_hash == phone_hash,
            User.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_identifier(self, identifier: str, identifier_type: str) -> User | None:
        """
        Fetch an active user by email or phone.

        Used by the identify endpoint to check existence.
        """
        if identifier_type == "phone":
            return await self.get_by_phone(identifier)
        return await self.get_by_email(identifier)