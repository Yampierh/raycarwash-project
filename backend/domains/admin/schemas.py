from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Users ──────────────────────────────────────────────────────────── #

class AdminUserRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    onboarding_status: str
    roles: list[str] = []
    permissions: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None


class AdminUsersListResponse(BaseModel):
    users: list[AdminUserRead]
    total: int
    page: int
    per_page: int


# ── Roles ──────────────────────────────────────────────────────────── #

class PermissionRead(BaseModel):
    id: uuid.UUID
    name: str
    resource: str
    action: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class RoleRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_system: bool
    permissions: list[PermissionRead] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None


# ── Permissions ────────────────────────────────────────────────────── #

class PermissionCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z_]+:[a-z_]+$", description="Format: action:resource")
    resource: str = Field(..., min_length=2, max_length=50)
    action: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None


class RolePermissionAssign(BaseModel):
    permission_id: uuid.UUID


class UserRoleAssign(BaseModel):
    role_id: uuid.UUID


# ── Stats ──────────────────────────────────────────────────────────── #

class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_detailers: int
    total_clients: int
    pending_verification: int
    total_appointments: int
    total_roles: int
    total_permissions: int
