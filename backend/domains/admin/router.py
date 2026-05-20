import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, get_args

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.admin.repository import AdminRepository
from domains.admin.schemas import (
    AdminAppointmentDetail,
    AdminAppointmentRead,
    AdminAppointmentStatusUpdate,
    AdminAppointmentsListResponse,
    AdminDetailerActionResponse,
    AdminDetailerApprove,
    AdminDetailerSuspend,
    AdminLedgerEntryRead,
    AdminReviewActionResponse,
    AdminReviewApprove,
    AdminReviewHide,
    AdminReviewQueueResponse,
    AdminReviewQueueRow,
    AdminLedgerListResponse,
    AdminPaymentSummary,
    AdminStats,
    AdminUserRead,
    AdminUserUpdate,
    AdminUsersListResponse,
    AdminVerificationRead,
    AdminVerificationReject,
    OpsCityRow,
    OpsDashboardResponse,
    OpsHeatmap,
    OpsKpis,
    OpsKpiValue,
    OpsWindow,
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


# ── Ops Dashboard (Plan 24 W2-A) ───────────────────────────────────── #


_HEATMAP_ROWS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_HEATMAP_HOURS = list(range(7, 23))  # 7am..10pm inclusive — 16 cells


def _resolve_window(window: OpsWindow, now: datetime) -> tuple[datetime, datetime]:
    if window == "1h":
        return now - timedelta(hours=1), now
    if window == "today":
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_of_day, now
    if window == "7d":
        return now - timedelta(days=7), now
    if window == "30d":
        return now - timedelta(days=30), now
    if window == "90d":
        return now - timedelta(days=90), now
    raise ValueError(f"Unsupported window: {window}")


def _build_heatmap(heat_rows: list[dict]) -> OpsHeatmap:
    """Bucket Postgres dow/hour rows into a 7×16 0..5 quantile grid.

    Postgres `extract(dow, ...)` returns 0=Sun..6=Sat; we shift so that
    Mon=0..Sun=6 to match the design's row labels."""
    grid = [[0] * len(_HEATMAP_HOURS) for _ in _HEATMAP_ROWS]
    counts: list[int] = []
    peak_n = -1
    peak_label = ""
    for row in heat_rows:
        pg_dow = row["dow"]  # 0=Sun..6=Sat
        hour = row["hour"]
        n = row["n"]
        # shift Sun(0) → 6; Mon(1) → 0; Tue(2) → 1; ...
        shifted_dow = (pg_dow + 6) % 7
        if hour not in _HEATMAP_HOURS:
            continue
        col = _HEATMAP_HOURS.index(hour)
        # store the raw count first; convert to level below
        grid[shifted_dow][col] = n
        counts.append(n)
        if n > peak_n:
            peak_n = n
            peak_label = f"{_HEATMAP_ROWS[shifted_dow]} {hour:02d}:00"

    # Bucket counts into 0..5 levels using a simple linear scaling on
    # the observed max. With low data volume this skews toward level 5
    # but it's the right shape for the design's heat scale and avoids a
    # heavy quantile sort.
    levels = [[0] * len(_HEATMAP_HOURS) for _ in _HEATMAP_ROWS]
    if peak_n > 0:
        for r in range(len(_HEATMAP_ROWS)):
            for c in range(len(_HEATMAP_HOURS)):
                v = grid[r][c]
                if v == 0:
                    levels[r][c] = 0
                else:
                    # Map (0, peak_n] to (0, 5] with ceil-style buckets.
                    levels[r][c] = max(1, min(5, round(v / peak_n * 5)))

    return OpsHeatmap(
        rows=_HEATMAP_ROWS,
        hours=_HEATMAP_HOURS,
        levels=levels,
        peak_label=peak_label,
    )


def _short_code(name: str, code: str) -> str:
    """3-letter abbrev for narrow columns. Prefers the canonical code
    when it's 3+ chars (e.g. `fwa`), else first 3 letters of the name."""
    if len(code) >= 3:
        return code[:3].upper()
    return name[:3].upper()


@router.get(
    "/ops/dashboard",
    response_model=OpsDashboardResponse,
    summary="Operations dashboard — KPIs, demand heatmap, city rollup",
)
async def get_ops_dashboard(
    window: OpsWindow = Query(default="7d", description="1h | today | 7d | 30d | 90d"),
    city: str = Query(default="all", description="City code or 'all'"),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> OpsDashboardResponse:
    if window not in get_args(OpsWindow):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported window: {window}",
        )

    now = datetime.now(timezone.utc)
    period_start, period_end = _resolve_window(window, now)
    data = await AdminRepository(db).get_ops_dashboard(
        period_start=period_start,
        period_end=period_end,
        city=city,
    )

    kpis = OpsKpis(
        gmv_cents=OpsKpiValue(value=float(data["gmv_cents"])),
        bookings=OpsKpiValue(value=float(data["bookings"])),
        active_jobs=OpsKpiValue(value=float(data["active_jobs"])),
        take_rate=OpsKpiValue(value=float(data["take_rate"])),
        csat=OpsKpiValue(value=float(data["csat"])),
        cancel_rate=OpsKpiValue(value=float(data["cancel_rate"])),
    )

    heatmap = _build_heatmap(data["heat_rows"])

    cities_rows: list[OpsCityRow] = []
    for c in data["cities"]:
        code = c["code"]
        cities_rows.append(
            OpsCityRow(
                code=code,
                name=c["name"],
                short=_short_code(c["name"], code),
                state=c["state"],
                status=c["status"],
                active=c["status"] == "active",
                detailers=data["per_city_detailers"].get(code, 0),
                online=data["per_city_online"].get(code, 0),
                jobs=data["per_city_jobs"].get(code, 0),
            )
        )

    return OpsDashboardResponse(
        window=window,
        period_start=period_start,
        period_end=period_end,
        city=city,
        kpis=kpis,
        heatmap=heatmap,
        cities=cities_rows,
    )


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


# ── Detailers (Plan 24 W2-C) ───────────────────────────────────────── #

@router.post(
    "/detailers/{provider_id}/approve",
    response_model=AdminDetailerActionResponse,
    summary="Approve a detailer application (or reinstate from suspended)",
)
async def approve_detailer(
    provider_id: uuid.UUID,
    body: AdminDetailerApprove | None = None,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminDetailerActionResponse:
    repo = AdminRepository(db)
    try:
        result = await repo.approve_detailer(
            provider_id=provider_id,
            actor_id=admin.id,
            notes=body.notes if body else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")
    await db.commit()
    prev, new_status, user_email = result
    return AdminDetailerActionResponse(
        provider_id=provider_id,
        user_email=user_email,
        application_status=new_status,  # type: ignore[arg-type]
        previous_status=prev,  # type: ignore[arg-type]
        reviewed_at=datetime.now(timezone.utc),
        rejection_reason=None,
    )


@router.post(
    "/detailers/{provider_id}/suspend",
    response_model=AdminDetailerActionResponse,
    summary="Suspend an approved detailer (reversible via /approve)",
)
async def suspend_detailer(
    provider_id: uuid.UUID,
    body: AdminDetailerSuspend,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminDetailerActionResponse:
    repo = AdminRepository(db)
    try:
        result = await repo.suspend_detailer(
            provider_id=provider_id,
            actor_id=admin.id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")
    await db.commit()
    prev, new_status, user_email = result
    return AdminDetailerActionResponse(
        provider_id=provider_id,
        user_email=user_email,
        application_status=new_status,  # type: ignore[arg-type]
        previous_status=prev,  # type: ignore[arg-type]
        reviewed_at=datetime.now(timezone.utc),
        rejection_reason=body.reason,
    )


# ── Reviews moderation (Plan 24 W2-D) ──────────────────────────────── #


@router.get(
    "/reviews/queue",
    response_model=AdminReviewQueueResponse,
    summary="Pending reviews flagged for moderation",
)
async def list_review_queue(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminReviewQueueResponse:
    rows = await AdminRepository(db).list_review_queue()
    return AdminReviewQueueResponse(
        reviews=[AdminReviewQueueRow(**r) for r in rows],
        total=len(rows),
    )


@router.post(
    "/reviews/{review_id}/approve",
    response_model=AdminReviewActionResponse,
    summary="Keep a flagged review visible",
)
async def approve_review(
    review_id: uuid.UUID,
    body: AdminReviewApprove | None = None,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminReviewActionResponse:
    repo = AdminRepository(db)
    try:
        result = await repo.approve_review(
            review_id=review_id,
            actor_id=admin.id,
            note=body.note if body else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    await db.commit()
    prev, new_state = result
    return AdminReviewActionResponse(
        review_id=review_id,
        moderation_state=new_state,  # type: ignore[arg-type]
        previous_state=prev,  # type: ignore[arg-type]
        moderation_acted_at=datetime.now(timezone.utc),
        moderation_note=body.note if body else None,
    )


@router.post(
    "/reviews/{review_id}/hide",
    response_model=AdminReviewActionResponse,
    summary="Hide a review (rating still counts; comment is suppressed)",
)
async def hide_review(
    review_id: uuid.UUID,
    body: AdminReviewHide,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminReviewActionResponse:
    repo = AdminRepository(db)
    try:
        result = await repo.hide_review(
            review_id=review_id, actor_id=admin.id, note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    await db.commit()
    prev, new_state = result
    return AdminReviewActionResponse(
        review_id=review_id,
        moderation_state=new_state,  # type: ignore[arg-type]
        previous_state=prev,  # type: ignore[arg-type]
        moderation_acted_at=datetime.now(timezone.utc),
        moderation_note=body.note,
    )


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
