"""
app/db/seed_rbac.py

Seeds system roles and permissions. Idempotent — safe to call on every startup.
Roles are marked is_system=True to prevent deletion via API.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import Permission, Role, RolePermission, UserRoleAssociation
from domains.users.models import User, OnboardingStatus

logger = logging.getLogger(__name__)

ROLE_DATA: list[dict] = [
    {
        "name": "admin",
        "description": "Full system access. Can manage users, roles, appointments, services, and all platform settings.",
    },
    {
        "name": "detailer",
        "description": "Professional detailer. Can manage their profile, services, working hours, and appointments assigned to them.",
    },
    {
        "name": "mechanic",
        "description": "Mobile mechanic. Can manage their profile, services, working hours, and appointments assigned to them. Integration plan E1 (01-profiles.md).",
    },
    {
        "name": "client",
        "description": "End customer. Can book appointments, manage their vehicles, and leave reviews.",
    },
]

# Format: (name, resource, action, description)
PERMISSION_DATA: list[tuple[str, str, str, str]] = [
    # Users
    ("read:users",        "users",       "read",   "View user profiles and list"),
    ("write:users",       "users",       "write",  "Create or update user accounts"),
    ("delete:users",      "users",       "delete", "Deactivate or soft-delete users"),
    # Roles & permissions
    ("read:roles",        "roles",       "read",   "View roles and their permissions"),
    ("write:roles",       "roles",       "write",  "Create or update roles"),
    ("delete:roles",      "roles",       "delete", "Delete non-system roles"),
    ("read:permissions",  "permissions", "read",   "View permission catalog"),
    ("write:permissions", "permissions", "write",  "Create or delete permissions"),
    # Appointments
    ("read:appointments",   "appointments", "read",   "View all appointments"),
    ("write:appointments",  "appointments", "write",  "Create or modify appointments"),
    ("delete:appointments", "appointments", "delete", "Cancel or delete appointments"),
    # Providers
    ("read:providers",  "providers", "read",  "View provider profiles and verification"),
    ("write:providers", "providers", "write", "Update provider profiles and verification"),
    # Payments
    ("read:payments", "payments", "read", "View payment records and refunds"),
    # Reviews
    ("read:reviews",   "reviews", "read",   "View all reviews"),
    ("delete:reviews", "reviews", "delete", "Remove inappropriate reviews"),
    # Services catalog
    ("read:services",  "services", "read",  "View service and addon catalog"),
    ("write:services", "services", "write", "Create or update services and addons"),
]

# Which permissions each role gets by default
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [p[0] for p in PERMISSION_DATA],  # admin gets all
    "detailer": [
        "read:appointments", "write:appointments",
        "read:providers", "write:providers",
        "read:reviews",
        "read:services",
    ],
    # E1.C: mechanic mirrors detailer's permission set. The vertical
    # differs at the catalog level (categories, service templates) but
    # the action surface — read/write bookings, read/write provider
    # profile, read reviews and services — is identical. Diverging
    # permissions only becomes necessary if a vertical-specific endpoint
    # ever needs gating.
    "mechanic": [
        "read:appointments", "write:appointments",
        "read:providers", "write:providers",
        "read:reviews",
        "read:services",
    ],
    "client": [
        "read:appointments", "write:appointments",
        "read:services",
        "read:reviews", "write:permissions",
    ],
}


async def seed_rbac(db: AsyncSession) -> None:
    """Seed roles and permissions. Idempotent."""
    # Seed roles
    roles_by_name: dict[str, Role] = {}
    for role_info in ROLE_DATA:
        result = await db.execute(select(Role).where(Role.name == role_info["name"]))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(name=role_info["name"], description=role_info["description"], is_system=True)
            db.add(role)
            await db.flush()
            logger.info("Created role: %s", role_info["name"])
        roles_by_name[role.name] = role

    # Seed permissions
    perms_by_name: dict[str, Permission] = {}
    for name, resource, action, description in PERMISSION_DATA:
        result = await db.execute(select(Permission).where(Permission.name == name))
        perm = result.scalar_one_or_none()
        if perm is None:
            perm = Permission(name=name, resource=resource, action=action, description=description)
            db.add(perm)
            await db.flush()
            logger.info("Created permission: %s", name)
        perms_by_name[name] = perm

    # Assign permissions to roles
    for role_name, perm_names in ROLE_PERMISSIONS.items():
        role = roles_by_name.get(role_name)
        if role is None:
            continue
        for perm_name in perm_names:
            perm = perms_by_name.get(perm_name)
            if perm is None:
                continue
            existing = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
            )
            if existing.scalar_one_or_none() is None:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await db.commit()
    logger.info("RBAC seed complete.")

    # Seed default admin user (dev only — change password in production)
    await _seed_admin_user(db, roles_by_name.get("admin"))


async def _seed_admin_user(db: AsyncSession, admin_role: Role | None) -> None:
    """Create a default admin user if none exists. Idempotent."""
    if admin_role is None:
        return

    ADMIN_EMAIL    = "admin@raycarwash.com"
    ADMIN_PASSWORD = "Admin1234!"

    existing = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
    if existing.scalar_one_or_none() is not None:
        return

    from domains.auth.service import AuthService
    user = User(
        email=ADMIN_EMAIL,
        full_name="Admin",
        password_hash=AuthService.hash_password(ADMIN_PASSWORD),
        is_active=True,
        onboarding_status=OnboardingStatus.COMPLETED,
    )
    db.add(user)
    await db.flush()
    db.add(UserRoleAssociation(user_id=user.id, role_id=admin_role.id))
    await db.commit()
    logger.info("Default admin user created: %s / %s", ADMIN_EMAIL, ADMIN_PASSWORD)
