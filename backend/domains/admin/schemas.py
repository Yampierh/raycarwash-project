from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


# ── Appointments ────────────────────────────────────────────────────── #

class AdminAppointmentRead(BaseModel):
    id: uuid.UUID
    status: str
    scheduled_time: datetime
    client_email: Optional[str] = None
    detailer_email: Optional[str] = None
    service_name: Optional[str] = None
    estimated_price: int
    actual_price: Optional[int] = None

    model_config = {"from_attributes": True}


class AdminAppointmentDetail(AdminAppointmentRead):
    client_notes: Optional[str] = None
    detailer_notes: Optional[str] = None
    service_address: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    arrived_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AdminAppointmentStatusUpdate(BaseModel):
    new_status: str


class AdminAppointmentsListResponse(BaseModel):
    appointments: list[AdminAppointmentRead]
    total: int
    page: int
    per_page: int


# ── Appointment refund + reassign (Plan 24 W2-B) ────────────────────── #

RefundReason = Literal["duplicate", "fraudulent", "requested_by_customer", "other"]


class AdminAppointmentRefund(BaseModel):
    amount_cents: int = Field(..., gt=0, description="Positive cents; capped to appointment price")
    reason: RefundReason = Field(default="requested_by_customer")
    note: Optional[str] = Field(default=None, max_length=500)


class AdminAppointmentRefundResponse(BaseModel):
    appointment_id: uuid.UUID
    refund_id: uuid.UUID
    stripe_refund_id: Optional[str] = None
    amount_cents: int
    status: str
    reason: str


class AdminAppointmentReassign(BaseModel):
    new_detailer_id: uuid.UUID
    reason: str = Field(..., min_length=5, max_length=500)


class AdminAppointmentReassignResponse(BaseModel):
    appointment_id: uuid.UUID
    previous_detailer_id: Optional[uuid.UUID] = None
    new_detailer_id: uuid.UUID
    appointment_status: str
    reason: str


# ── Verifications ───────────────────────────────────────────────────── #

class AdminVerificationRead(BaseModel):
    provider_id: uuid.UUID
    user_email: Optional[str] = None
    legal_full_name: Optional[str] = None
    verification_status: str
    background_check_consent: bool
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class AdminVerificationReject(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


# ── Detailers (Plan 24 W2-C) ────────────────────────────────────────── #

# Sanctioned set of application_status states. The FSM transitions are
# enforced at the repository layer; this Literal just documents the
# contract and gives Pydantic a tight validator for the response shape.
ApplicationStatusValue = Literal[
    "draft",
    "submitted",
    "bg_check_pending",
    "docs_review",
    "approved",
    "rejected",
    "suspended",
]


class AdminDetailerApprove(BaseModel):
    """Optional context an admin can attach to an approve transition.

    Used for both `submitted → approved` (initial onboarding) and
    `suspended → approved` (reinstate). Empty body is allowed."""

    notes: Optional[str] = Field(default=None, max_length=500)


class AdminDetailerSuspend(BaseModel):
    """Reason required — surfaced in the detailer-facing notification
    and stored on `provider_profiles.rejection_reason` for the support
    audit trail."""

    reason: str = Field(..., min_length=5, max_length=500)


class AdminDetailerActionResponse(BaseModel):
    provider_id: uuid.UUID
    user_email: Optional[str] = None
    application_status: ApplicationStatusValue
    previous_status: ApplicationStatusValue
    reviewed_at: datetime
    rejection_reason: Optional[str] = None


# ── Reviews moderation (Plan 24 W2-D) ───────────────────────────────── #

ReviewModerationState = Literal["auto_pending", "approved", "hidden"]


class AdminReviewQueueRow(BaseModel):
    """One pending review surfaced to the moderation queue. `flag_reasons`
    is computed at query time — `low_rating` for rating ≤ 2 and
    `keyword:<word>` for each profanity hit."""

    review_id: uuid.UUID
    appointment_id: uuid.UUID
    reviewer_email: Optional[str] = None
    detailer_email: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    flag_reasons: list[str] = Field(default_factory=list)
    created_at: datetime


class AdminReviewQueueResponse(BaseModel):
    reviews: list[AdminReviewQueueRow]
    total: int


class AdminReviewApprove(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)


class AdminReviewHide(BaseModel):
    note: str = Field(..., min_length=5, max_length=500)


class AdminReviewActionResponse(BaseModel):
    review_id: uuid.UUID
    moderation_state: ReviewModerationState
    previous_state: ReviewModerationState
    moderation_acted_at: datetime
    moderation_note: Optional[str] = None


# ── Customers + comp credits (Plan 24 W2-E) ─────────────────────────── #

CustomerSegment = Literal["all", "new", "active", "dormant", "vip"]
CreditSource = Literal["admin_comp", "promo", "referral", "refund", "adjustment"]


class AdminCustomerRow(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    segment: Literal["new", "active", "dormant", "vip"]
    appointments_count: int
    last_appointment_at: Optional[datetime] = None
    lifetime_spend_cents: int
    credit_balance_cents: int
    created_at: datetime


class AdminCustomersListResponse(BaseModel):
    customers: list[AdminCustomerRow]
    total: int
    page: int
    per_page: int


class AdminCreditIssue(BaseModel):
    amount_cents: int = Field(..., gt=0, le=10_000_00, description="Positive cents; max $10,000")
    reason: str = Field(..., min_length=5, max_length=500)
    source: CreditSource = Field(default="admin_comp")
    expires_at: Optional[datetime] = None
    related_appointment_id: Optional[uuid.UUID] = None


class AdminCreditRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount_cents: int
    currency: str
    reason: str
    source: str
    status: str
    issued_by: Optional[uuid.UUID] = None
    related_appointment_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Payments ────────────────────────────────────────────────────────── #

class AdminLedgerEntryRead(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    entry_type: str
    amount_cents: int
    currency: str
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminLedgerListResponse(BaseModel):
    entries: list[AdminLedgerEntryRead]
    total: int
    page: int
    per_page: int


class AdminPaymentSummary(BaseModel):
    total_captured: int
    total_refunded: int
    total_commissions: int
    total_payouts: int
    net_revenue: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# ── Ops Dashboard (Plan 24 W2-A) ────────────────────────────────────── #

OpsWindow = Literal["1h", "today", "7d", "30d", "90d"]


class OpsKpiValue(BaseModel):
    """A single KPI tile. `delta` and `spark` are reserved for future
    iterations — set to 0 / [] in V1 so the frontend can render the
    tile shell without breaking."""

    value: float
    delta: float = 0.0
    spark: list[float] = Field(default_factory=list)


class OpsKpis(BaseModel):
    gmv_cents: OpsKpiValue
    bookings: OpsKpiValue
    active_jobs: OpsKpiValue
    take_rate: OpsKpiValue
    csat: OpsKpiValue
    cancel_rate: OpsKpiValue


class OpsHeatmap(BaseModel):
    """7-day × 16-hour demand grid keyed by `scheduled_time`. Hours run
    from `hour_start` to `hour_start + len(hours) - 1` (local-equivalent
    UTC for V1). Level is a 0–5 quantile bucket per cell across the
    grid."""

    rows: list[str]            # ["Mon", "Tue", ..., "Sun"]
    hours: list[int]           # [7, 8, ..., 22]
    levels: list[list[int]]    # 7 × 16, integers 0..5
    peak_label: str = ""       # e.g. "Sat 11:00" — empty if no data


class OpsCityRow(BaseModel):
    code: str
    name: str
    short: str                  # 3-letter abbrev for narrow columns
    state: str
    status: str                 # active | pilot | planned | paused
    active: bool                # status == "active"
    detailers: int              # approved provider profiles in this city
    online: int                 # approximation: detailers with an in-flight appointment right now
    jobs: int                   # in-flight appointment count (CONFIRMED/ARRIVED/IN_PROGRESS) in window
    surge: float = 1.0          # placeholder until surge_rules engine ships (Wave 4)


class OpsDashboardResponse(BaseModel):
    window: OpsWindow
    period_start: datetime
    period_end: datetime
    city: str                   # "all" or a city code
    kpis: OpsKpis
    heatmap: OpsHeatmap
    cities: list[OpsCityRow]


# ── Audit Log ───────────────────────────────────────────────────────── #

class AdminAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_email: str | None  # joined from actor user
    action: str
    entity_type: str
    entity_id: str
    ip_address: str | None
    created_at: datetime


class AdminAuditLogsListResponse(BaseModel):
    entries: list[AdminAuditLogRead]
    total: int
    page: int
    per_page: int
