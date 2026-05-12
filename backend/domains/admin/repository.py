from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import (
    Permission,
    Role,
    RolePermission,
    UserRoleAssociation,
)
from domains.users.models import User


class AdminRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Users ──────────────────────────────────────────────────────── #

    async def list_users(
        self,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        role_filter: str | None = None,
    ) -> tuple[list[User], int]:
        """Paginated user list with optional search and role filter."""
        base = (
            select(User)
            .where(User.is_deleted.is_(False))
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRoleAssociation.role)
                .selectinload(Role.permissions)
            )
            .execution_options(populate_existing=True)
        )

        if search:
            base = base.where(User.email.ilike(f"%{search}%"))

        if role_filter:
            base = base.join(
                UserRoleAssociation, UserRoleAssociation.user_id == User.id
            ).join(Role, Role.id == UserRoleAssociation.role_id).where(
                Role.name == role_filter
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_user_with_roles(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id, User.is_deleted.is_(False))
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRoleAssociation.role)
                .selectinload(Role.permissions)
            )
            .execution_options(populate_existing=True)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def set_user_active(self, user_id: uuid.UUID, is_active: bool) -> bool:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=is_active, updated_at=datetime.now(timezone.utc))
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

    async def assign_role_to_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID,
    ) -> bool:
        """Assign a role to a user. Idempotent — no error if already assigned."""
        existing = await self._db.execute(
            select(UserRoleAssociation).where(
                UserRoleAssociation.user_id == user_id,
                UserRoleAssociation.role_id == role_id,
            )
        )
        if existing.scalar_one_or_none():
            return False

        self._db.add(UserRoleAssociation(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
        ))
        await self._db.flush()
        return True

    async def revoke_role_from_user(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        stmt = delete(UserRoleAssociation).where(
            UserRoleAssociation.user_id == user_id,
            UserRoleAssociation.role_id == role_id,
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

    # ── Roles ──────────────────────────────────────────────────────── #

    async def list_roles(self) -> list[Role]:
        stmt = (
            select(Role)
            .where(Role.is_deleted.is_(False))
            .options(selectinload(Role.permissions))
            .order_by(Role.name)
            .execution_options(populate_existing=True)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.id == role_id, Role.is_deleted.is_(False))
            .options(selectinload(Role.permissions))
            .execution_options(populate_existing=True)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name, Role.is_deleted.is_(False))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_role(self, name: str, description: str | None = None) -> Role:
        role = Role(name=name, description=description, is_system=False)
        self._db.add(role)
        await self._db.flush()
        # Re-fetch with permissions eager-loaded so RoleRead can serialize
        return await self.get_role_by_id(role.id)  # type: ignore[return-value]

    async def update_role(self, role_id: uuid.UUID, fields: dict) -> Role | None:
        role = await self.get_role_by_id(role_id)
        if role is None or role.is_system:
            return None
        for key, value in fields.items():
            setattr(role, key, value)
        await self._db.flush()
        # Re-fetch so updated fields + permissions are fresh
        return await self.get_role_by_id(role_id)

    async def delete_role(self, role_id: uuid.UUID) -> bool:
        """Soft-delete a role. Refuses to delete system roles."""
        role = await self.get_role_by_id(role_id)
        if role is None:
            return False
        if role.is_system:
            raise ValueError(f"System role '{role.name}' cannot be deleted.")
        role.is_deleted = True
        role.deleted_at = datetime.now(timezone.utc)
        await self._db.flush()
        return True

    async def assign_permission_to_role(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> bool:
        """Idempotent — no error if already assigned."""
        existing = await self._db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        if existing.scalar_one_or_none():
            return False
        self._db.add(RolePermission(role_id=role_id, permission_id=permission_id))
        await self._db.flush()
        return True

    async def revoke_permission_from_role(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> bool:
        stmt = delete(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

    # ── Permissions ────────────────────────────────────────────────── #

    async def list_permissions(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.resource, Permission.action)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_permission_by_id(self, permission_id: uuid.UUID) -> Permission | None:
        stmt = select(Permission).where(Permission.id == permission_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_permission(
        self,
        name: str,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> Permission:
        perm = Permission(name=name, resource=resource, action=action, description=description)
        self._db.add(perm)
        await self._db.flush()
        await self._db.refresh(perm)
        return perm

    async def delete_permission(self, permission_id: uuid.UUID) -> bool:
        perm = await self.get_permission_by_id(permission_id)
        if perm is None:
            return False
        await self._db.execute(
            delete(RolePermission).where(RolePermission.permission_id == permission_id)
        )
        await self._db.execute(delete(Permission).where(Permission.id == permission_id))
        await self._db.flush()
        return True

    # ── Stats ──────────────────────────────────────────────────────── #

    async def get_stats(self) -> dict:
        from domains.auth.models import Role as RoleModel
        from domains.users.models import User as UserModel

        total_users = (await self._db.execute(
            select(func.count(UserModel.id)).where(UserModel.is_deleted.is_(False))
        )).scalar_one()

        active_users = (await self._db.execute(
            select(func.count(UserModel.id)).where(
                UserModel.is_deleted.is_(False), UserModel.is_active.is_(True)
            )
        )).scalar_one()

        total_detailers = (await self._db.execute(
            select(func.count(UserModel.id))
            .join(UserRoleAssociation, UserRoleAssociation.user_id == UserModel.id)
            .join(RoleModel, RoleModel.id == UserRoleAssociation.role_id)
            .where(RoleModel.name == "detailer", UserModel.is_deleted.is_(False))
        )).scalar_one()

        total_clients = (await self._db.execute(
            select(func.count(UserModel.id))
            .join(UserRoleAssociation, UserRoleAssociation.user_id == UserModel.id)
            .join(RoleModel, RoleModel.id == UserRoleAssociation.role_id)
            .where(RoleModel.name == "client", UserModel.is_deleted.is_(False))
        )).scalar_one()

        # Providers pending verification
        try:
            from domains.providers.models import ProviderProfile
            pending_verification = (await self._db.execute(
                select(func.count(ProviderProfile.id)).where(
                    ProviderProfile.verification_status == "not_submitted"
                )
            )).scalar_one()
        except Exception:
            pending_verification = 0

        # Total appointments
        try:
            from domains.appointments.models import Appointment
            total_appointments = (await self._db.execute(
                select(func.count(Appointment.id))
            )).scalar_one()
        except Exception:
            total_appointments = 0

        total_roles = (await self._db.execute(
            select(func.count(RoleModel.id)).where(RoleModel.is_deleted.is_(False))
        )).scalar_one()

        total_permissions = (await self._db.execute(
            select(func.count(Permission.id))
        )).scalar_one()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_detailers": total_detailers,
            "total_clients": total_clients,
            "pending_verification": pending_verification,
            "total_appointments": total_appointments,
            "total_roles": total_roles,
            "total_permissions": total_permissions,
        }
