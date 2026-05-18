# Architecture & Execution Protocol Violations

> **Date**: 2026-05-17
> **Scope**: Full backend architecture analysis
> **Related**: `execution_protocol.md`, AGENTS.md business rules

---

## 1. CRITICAL: Service Layer Contains SQL

### 1.1 PaymentService — Inline SQL for Appointment queries

**File**: `backend/domains/payments/service.py`
**Lines**: 106-111, 392-396

```python
# Violation: raw select() instead of AppointmentRepository
result = await db.execute(
    select(Appointment).where(Appointment.id == appointment_id)
)
appointment = result.scalar_one_or_none()
```

**Problem**: Services MUST have zero SQL per execution protocol. `PaymentService` bypasses `AppointmentRepository` entirely.

### 1.2 MatchingService — Inline SQL + Direct db.commit()

**File**: `backend/domains/matching/service.py`
**Lines**: 65-72, 97, 120-124, 125, 134, 143-150

- Raw `select(ProviderProfile)` and `update(Appointment)` instead of repositories
- Calls `db.commit()` directly — breaks normal transaction boundary managed by FastAPI dependency

### 1.3 Providers Router — SQLAlchemy imports

**File**: `backend/domains/providers/router.py`
**Line**: 21

```python
from sqlalchemy import and_, delete, func, select
```

Router executes raw ORM operations, bypassing repository layer entirely.

---

## 2. CRITICAL: AdminRepository Contains Business Logic

**File**: `backend/domains/admin/repository.py`

Repository handles business operations instead of data access:
- `force_appointment_status()` — writes audit logs, bypasses FSM
- `approve_verification()` — modifies profile state
- `reject_verification()` — modifies profile state

**Fix**: These should be in an `AdminService`. Repository should only do CRUD.

---

## 3. HIGH: VehicleSize Violation (Business Rule)

**File**: `backend/domains/appointments/models.py`
**Lines**: 151-153

**AGENTS.md states**: "VehicleSize is runtime-derived via map_body_to_size(body_class). Never stored — do NOT add a size column."

But `AppointmentVehicle` join table HAS a `vehicle_size` column that stores a snapshot at booking time.

**Debate**: This may be intentional (audit snapshot for pricing), but it contradicts the explicit rule. If kept, the rule should be updated to allow it with a comment explaining why.

---

## 4. HIGH: Empty Service Files

| Service File | Status |
|-------------|--------|
| `backend/domains/providers/service.py` | Empty — comment says "Provider logic lives in detailer_router.py" |
| `backend/domains/users/service.py` | Empty — logic spread across 9 separate routers |
| `backend/domains/vehicles/service.py` | Empty — just re-exports `map_body_to_size` |

**Impact**: Business logic leaks into routers and repositories, violating DDD-lite.

---

## 5. HIGH: Seed RBAC — `client` Role Has Dangerous Permission

**File**: `backend/app/db/seed_rbac.py`
**Line**: 75

```python
Role(
    name="client",
    permissions=[..., "write:permissions"],  # ??? WHY???
```

The `client` role includes `write:permissions` — this is a security violation. Clients should NEVER have permission to write permissions.

---

## 6. HIGH: Domain Violation — Infrastructure Imports from Domain

**File**: `backend/infrastructure/nhtsa/client.py`
**Line**: 14

```python
from domains.vehicles.models import VehicleSize  # INFRA → DOMAIN import
```

Infrastructure should NEVER depend on domain code. `VehicleSize` should live in `shared/` or be passed as a parameter.

---

## 7. MEDIUM: Pricing Config Lives in Seed File

**File**: `backend/app/db/seed.py`
**Line**: 23

```python
SIZE_MULTIPLIERS = {  # Pricing constants imported by AppointmentService
```

Comment says "do NOT move to another module" but this is a layering violation. Pricing constants should be in `shared/constants.py` or `domains/appointments/constants.py`.

---

## 8. MEDIUM: Cross-Domain Direct Coupling

| Source | Target | Method | File |
|--------|--------|--------|------|
| `ReviewRepository` | `ProviderProfile.average_rating` | Direct mutation | `reviews/repository.py` |
| `PaymentService` | `Appointment` | Raw SQL | `payments/service.py` |
| `MatchingService` | `Appointment` | Raw SQL | `matching/service.py` |

**Fix**: Use domain events via EventBus for cross-domain state changes instead of direct calls.

---

## 9. MEDIUM: AuthService Direct Model Mutation

**File**: `backend/domains/auth/service.py`
**Lines**: 550, 568-570

```python
# Direct model attribute mutation instead of repository method
user.failed_login_attempts += 1
user.locked_until = ...
```

Should use a `UserRepository.update_login_attempts()` method.

---

## 10. MEDIUM: `datetime.utcnow()` in VehicleRepository

**File**: `backend/domains/vehicles/repository.py`
**Line**: 48

```python
deleted_at=datetime.utcnow()  # naive datetime!
```

All other code uses `datetime.now(timezone.utc)` (timezone-aware). This naive datetime will be compared against timezone-aware columns and could cause timezone-based issues.

---

## 11. MEDIUM: `Envelope[T]` Compliance Gaps

Majority of routers do NOT use `EnvelopeRouter`:

| Router | Type | Status |
|--------|------|--------|
| Appointments | Plain `APIRouter` | ❌ |
| Vehicles | Plain `APIRouter` | ❌ |
| Matching | Plain `APIRouter` | ❌ |
| Admin | Plain `APIRouter` | ❌ |
| Reviews | Plain `APIRouter` | ❌ |
| Providers | Plain `APIRouter` | ❌ |
| Payments | Plain `APIRouter` | ❌ |
| Services | Plain `APIRouter` | ❌ |

Only `Users` domain uses `EnvelopeRouter`. The CI test `test_envelope_compliance.py` has a legacy allow-list that bypasses these.

### Raw dict responses found:

| File | Line | Response |
|------|------|----------|
| `appointments/router.py` | 214, 274-279 | `PaginatedResponse.build().model_dump()` |
| `reviews/router.py` | 45, 60-65 | `PaginatedResponse.build().model_dump()` |
| `providers/router.py` | 86, 122-125 | `PaginatedResponse.build().model_dump()` |
| `providers/router.py` | 276, 295 | bare `{}` |
| `providers/router.py` | 348, 405 | bare `{}` |
| `admin/router.py` | 259-266 | `{"message": "Permission assigned."}` |

---

## 12. LOW: State Machine — Missing Transitions

**File**: `backend/domains/appointments/models.py`
**Lines**: 26-27, 44-69

- `SEARCHING` and `NO_DETAILER_FOUND` enum values exist but have NO entries in `VALID_TRANSITIONS`
- `ARRIVED → NO_SHOW` transition is missing (a detailer arriving but marking no-show should be valid)
- 18 total valid transitions, only 7 tested

---

## 13. LOW: Missing Repositories

| Missing Repository | Impact |
|-------------------|--------|
| `PaymentsRepository` | PaymentService uses inline SQL for Appointment |
| `MatchingRepository` | Matching service uses inline SQL for ProviderProfile |
| `ClientProfileRepository` | Client profile created inline in auth routers |

---

## 14. LOW: IdempotencyMiddleware — `request.state.user` Not Set

**File**: `backend/main.py` — middleware stack comment

`IdempotencyMiddleware` is innermost and needs `request.state.user` from auth dependencies — but these are NOT set by middleware, only by `Depends(get_current_user)` inside route handlers. The middleware will always see `request.state.user` as potentially missing.

---

## 15. LOW: `app.state.assignment_events` and `assignment_responses`

**File**: `backend/main.py`

These are plain in-memory dicts, NOT shared across uvicorn workers. In multi-worker deployment, the assignment engine silently fails because each worker has a separate `app.state`. Needs Redis-backed pub/sub.

---

## Summary — Action Items by Priority

| Priority | Action | Affected Code |
|----------|--------|---------------|
| P0 | Fix `write:permissions` on client role | `app/db/seed_rbac.py:75` |
| P0 | Extract SQL from services into repositories | `payments/service.py`, `matching/service.py`, `providers/router.py` |
| P0 | Create `AdminService` for business logic | `admin/repository.py` |
| P1 | Move `VehicleSize` to shared/ | `infrastructure/nhtsa/client.py:14` |
| P1 | Add `Envelope[T]` to all legacy routers | All non-compliant routers |
| P1 | Move `SIZE_MULTIPLIERS` to shared constants | `app/db/seed.py:23` |
| P1 | Fix `datetime.utcnow()` | `vehicles/repository.py:48` |
| P2 | Add missing FSM transitions | `appointments/models.py` |
| P2 | Create missing repositories | Payments, Matching, ClientProfile |
| P2 | Migrate cross-domain direct calls to events | Reviews→Providers, Payments→Appointments |
| P3 | Fix `AuthService` direct model mutation | `auth/service.py` |
| P3 | Replace `app.state` dicts with Redis | `main.py` (assignment workers) |
