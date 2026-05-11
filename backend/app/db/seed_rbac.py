"""
app/db/seed_rbac.py

Seeds system roles and permissions. Idempotent — safe to call on every startup.
Roles are marked is_system=True to prevent deletion via API.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import Permission, Role, RolePermission

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
