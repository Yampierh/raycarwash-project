# app/db/seed_rbac.py
"""
RBAC seed: Creates system roles for the application.

This must run BEFORE seed_detailers() so that roles exist
when detailer users are created and assigned to roles.

Idempotent: safe to call on every startup (checks by role name).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Role

logger = logging.getLogger(__name__)

ROLE_DATA: list[dict[str, str]] = [
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


async def seed_rbac(db: AsyncSession) -> None:
    """
    Seed the base RBAC roles (admin, detailer, client).
    
    Each role is marked as is_system=True to prevent deletion via API.
    This function is idempotent — calling it multiple times is safe.
    """
    seeded = 0
    
    for role_info in ROLE_DATA:
        # Check if role already exists
        result = await db.execute(
            select(Role).where(Role.name == role_info["name"])
        )
        existing = result.scalar_one_or_none()
        
        if existing is not None:
            logger.debug("Role already exists: %s", role_info["name"])
            continue
        
        # Create new role
        role = Role(
            name=role_info["name"],
            description=role_info["description"],
            is_system=True,
        )
        db.add(role)
        seeded += 1
        logger.info("Created role: %s", role_info["name"])
    
    if seeded > 0:
        await db.commit()
        logger.info("RBAC seed complete — %d new role(s) inserted.", seeded)
    else:
        logger.info("RBAC seed: all roles already exist.")