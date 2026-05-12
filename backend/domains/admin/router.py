import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.admin.repository import AdminRepository
from domains.admin.schemas import (
    AdminAppointmentDetail,
    AdminAppointmentRead,
    AdminAppointmentStatusUpdate,
    AdminAppointmentsListResponse,
    AdminLedgerEntryRead,
    AdminLedgerListResponse,
    AdminPaymentSummary,
    AdminStats,
    AdminUserRead,
    AdminUserUpdate,
    AdminUsersListResponse,
    AdminVerificationRead,
    AdminVerificationReject,
    PermissionCreate,
    PermissionRead,
    RoleCreate,
    RolePermissionAssign,
    RoleRead,
    RoleUpdate,
    UserRoleAssign,
)
from domains.auth.service import require_role
from domains.users.models import User

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ── Stats ──────────────────────────────────────────────────────────── #

@router.get(
    "/stats",
    response_model=AdminStats,
    summary="Platform overview statistics",
)
async def get_stats(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminStats:
    data = await AdminRepository(db).get_stats()
    return AdminStats(**data)


# ── Users ──────────────────────────────────────────────────────────── #

@router.get(
    "/users",
    response_model=AdminUsersListResponse,
    summary="List all users (paginated)",
)
async def list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, description="Filter by email"),
    role: str | None = Query(default=None, description="Filter by role name"),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminUsersListResponse:
    users, total = await AdminRepository(db).list_users(
        page=page, per_page=per_page, search=search, role_filter=role
    )
    return AdminUsersListResponse(
        users=[_user_to_read(u) for u in users],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserRead,
    summary="Get user detail with roles and permissions",
)
async def get_user(
    user_id: uuid.UUID,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminUserRead:
    user = await AdminRepository(db).get_user_with_roles(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _user_to_read(user)


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserRead,
    summary="Update user status (active/inactive)",
)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminUserRead:
    repo = AdminRepository(db)
    if body.is_active is not None:
        ok = await repo.set_user_active(user_id, body.is_active)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    await db.commit()
    user = await repo.get_user_with_roles(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _user_to_read(user)


@router.get(
    "/users/{user_id}/roles",
    response_model=list[RoleRead],
    summary="List roles assigned to a user",
)
async def get_user_roles(
    user_id: uuid.UUID,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[RoleRead]:
    user = await AdminRepository(db).get_user_with_roles(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return [RoleRead.model_validate(ur.role) for ur in user.user_roles]


@router.post(
    "/users/{user_id}/roles",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a role to a user",
)
async def assign_role_to_user(
    user_id: uuid.UUID,
    body: UserRoleAssign,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    repo = AdminRepository(db)
    role = await repo.get_role_by_id(body.role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
    await repo.assign_role_to_user(user_id, body.role_id, assigned_by=admin.id)
    await db.commit()
    return RoleRead.model_validate(role)


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a role from a user",
)
async def revoke_role_from_user(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await AdminRepository(db).revoke_role_from_user(user_id, role_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found.")
    await db.commit()


# ── Roles ──────────────────────────────────────────────────────────── #

@router.get(
    "/roles",
    response_model=list[RoleRead],
    summary="List all roles with their permissions",
)
async def list_roles(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[RoleRead]:
    roles = await AdminRepository(db).list_roles()
    return [RoleRead.model_validate(r) for r in roles]


@router.post(
    "/roles",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new role",
)
async def create_role(
    body: RoleCreate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    repo = AdminRepository(db)
    existing = await repo.get_role_by_name(body.name)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Role '{body.name}' already exists.")
    role = await repo.create_role(body.name, body.description)
    await db.commit()
    await db.refresh(role)
    return RoleRead.model_validate(role)


@router.patch(
    "/roles/{role_id}",
    response_model=RoleRead,
    summary="Update a role (non-system only)",
)
async def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    role = await AdminRepository(db).update_role(role_id, fields)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found or is a system role (cannot be modified).",
        )
    await db.commit()
    return RoleRead.model_validate(role)


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role (non-system only)",
)
async def delete_role(
    role_id: uuid.UUID,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        ok = await AdminRepository(db).delete_role(role_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
    await db.commit()


@router.post(
    "/roles/{role_id}/permissions",
    status_code=status.HTTP_201_CREATED,
    summary="Assign a permission to a role",
)
async def assign_permission_to_role(
    role_id: uuid.UUID,
    body: RolePermissionAssign,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = AdminRepository(db)
    perm = await repo.get_permission_by_id(body.permission_id)
    if perm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found.")
    await repo.assign_permission_to_role(role_id, body.permission_id)
    await db.commit()
    return {"message": "Permission assigned."}


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a permission from a role",
)
async def revoke_permission_from_role(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await AdminRepository(db).revoke_permission_from_role(role_id, permission_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission assignment not found.")
    await db.commit()


# ── Permissions ────────────────────────────────────────────────────── #

@router.get(
    "/permissions",
    response_model=list[PermissionRead],
    summary="List all permissions",
)
async def list_permissions(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[PermissionRead]:
    perms = await AdminRepository(db).list_permissions()
    return [PermissionRead.model_validate(p) for p in perms]


@router.post(
    "/permissions",
    response_model=PermissionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new permission",
)
async def create_permission(
    body: PermissionCreate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> PermissionRead:
    perm = await AdminRepository(db).create_permission(
        name=body.name,
        resource=body.resource,
        action=body.action,
        description=body.description,
    )
    await db.commit()
    return PermissionRead.model_validate(perm)


@router.delete(
    "/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a permission (removes it from all roles)",
)
async def delete_permission(
    permission_id: uuid.UUID,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await AdminRepository(db).delete_permission(permission_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found.")
    await db.commit()


# ── Appointments ───────────────────────────────────────────────────── #

@router.get(
    "/appointments",
    response_model=AdminAppointmentsListResponse,
    summary="List all appointments (paginated, filterable)",
)
async def list_appointments(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by appointment status"),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Search by client/detailer email"),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminAppointmentsListResponse:
    rows, total = await AdminRepository(db).list_appointments(
        page=page, per_page=per_page, status=status,
        start_date=start_date, end_date=end_date, search=search,
    )
    return AdminAppointmentsListResponse(
        appointments=[AdminAppointmentRead(**r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/appointments/{appointment_id}",
    response_model=AdminAppointmentDetail,
    summary="Get appointment detail",
)
async def get_appointment(
    appointment_id: uuid.UUID,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminAppointmentDetail:
    data = await AdminRepository(db).get_appointment_detail(appointment_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return AdminAppointmentDetail(**data)


@router.patch(
    "/appointments/{appointment_id}/status",
    response_model=AdminAppointmentDetail,
    summary="Force appointment status (admin override)",
)
async def force_appointment_status(
    appointment_id: uuid.UUID,
    body: AdminAppointmentStatusUpdate,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminAppointmentDetail:
    repo = AdminRepository(db)
    ok = await repo.force_appointment_status(appointment_id, body.new_status, admin.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    await db.commit()
    data = await repo.get_appointment_detail(appointment_id)
    return AdminAppointmentDetail(**data)  # type: ignore[arg-type]


# ── Verifications ──────────────────────────────────────────────────── #

@router.get(
    "/verifications",
    response_model=list[AdminVerificationRead],
    summary="List detailer verification requests",
)
async def list_verifications(
    verification_status: Optional[str] = Query(default=None, description="Filter: pending | approved | rejected"),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[AdminVerificationRead]:
    rows = await AdminRepository(db).list_verifications(status_filter=verification_status)
    return [AdminVerificationRead(**r) for r in rows]


@router.post(
    "/verifications/{provider_id}/approve",
    response_model=AdminVerificationRead,
    summary="Approve a detailer verification",
)
async def approve_verification(
    provider_id: uuid.UUID,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminVerificationRead:
    repo = AdminRepository(db)
    ok = await repo.approve_verification(provider_id, admin.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")
    await db.commit()
    rows = await repo.list_verifications()
    match = next((r for r in rows if r["provider_id"] == provider_id), None)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")
    return AdminVerificationRead(**match)


@router.post(
    "/verifications/{provider_id}/reject",
    response_model=AdminVerificationRead,
    summary="Reject a detailer verification",
)
async def reject_verification(
    provider_id: uuid.UUID,
    body: AdminVerificationReject,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminVerificationRead:
    repo = AdminRepository(db)
    ok = await repo.reject_verification(provider_id, body.reason, admin.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")
    await db.commit()
    rows = await repo.list_verifications()
    match = next((r for r in rows if r["provider_id"] == provider_id), None)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")
    return AdminVerificationRead(**match)


# ── Payments ───────────────────────────────────────────────────────── #

@router.get(
    "/payments/summary",
    response_model=AdminPaymentSummary,
    summary="Payment summary for a time period",
)
async def get_payment_summary(
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminPaymentSummary:
    data = await AdminRepository(db).get_payment_summary(start_date, end_date)
    return AdminPaymentSummary(**data)


@router.get(
    "/payments/ledger",
    response_model=AdminLedgerListResponse,
    summary="Paginated payment ledger entries",
)
async def list_ledger_entries(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    entry_type: Optional[str] = Query(default=None, description="CAPTURE | REFUND | PAYOUT | CHARGE_COMMISSION | AUTHORIZATION"),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminLedgerListResponse:
    entries, total = await AdminRepository(db).list_ledger_entries(
        page=page, per_page=per_page,
        entry_type=entry_type, start_date=start_date, end_date=end_date,
    )
    return AdminLedgerListResponse(
        entries=[AdminLedgerEntryRead.model_validate(e) for e in entries],
        total=total,
        page=page,
        per_page=per_page,
    )


# ── Helpers ────────────────────────────────────────────────────────── #

def _user_to_read(user: User) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        onboarding_status=user.onboarding_status,
        roles=user.roles,
        permissions=list(user.get_all_permissions()),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
