---
name: backend-api-design
description: REST API design principles for FastAPI backends. Use when creating new routers, adding endpoints, or modifying existing ones. Follows the RayCarWash path conventions, auth patterns, and error format.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - state_machine
  - failure_modes
preconditions:
  - system_contracts loaded (request lifecycle understood)
  - Schema defined before endpoint code
outputs:
  - Router endpoint with full documentation
  - Pydantic request/response schemas
conflicts:
  - Never return raw dicts instead of schemas
  - Never bypass api/router.py aggregation
  - Never skip ErrorDetail for errors
execution_priority: 2
---

# REST API Design for FastAPI

**Priority: CRITICAL**  
**Applies to:** New endpoints, router modifications, API contracts

## Naming Conventions

| Resource | Path | Methods |
|----------|------|---------|
| Auth | `/api/v1/auth` | POST |
| Users | `/api/v1/users` | GET, POST |
| Vehicles | `/api/v1/vehicles` | GET, POST, PUT, DELETE |
| Appointments | `/api/v1/appointments` | GET, POST, PATCH |
| Detailers | `/api/v1/detailers` | GET, PUT, PATCH |
| Services | `/api/v1/services` | GET |
| Matching | `/api/v1/matching` | GET |
| Webhooks | `/webhooks/{provider}` | POST |
| Health | `/health` | GET |

**Rules:**
- All paths start with `/api/v1/` for domain routes
- Webhooks live at root `/webhooks/`
- Health checks at root `/health`
- Use plural nouns: `vehicles`, not `vehicle`
- Use kebab-case for multi-word paths: `detailer-selection`

## Router Structure

### Placement

```
domains/{domain}/
├── models.py
├── repository.py
├── service.py
├── router.py       ← Router lives here
└── schemas.py
```

### Aggregation

All routers are aggregated via `api/router.py`. **Never include routers directly in `main.py`.**

```python
# api/router.py
from fastapi import APIRouter
from domains.appointments.router import router as appointments_router
# ... other imports

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(appointments_router)
```

### Basic Endpoint Template

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.auth import get_current_user
from domains.appointments.schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatusUpdate,
)
from domains.appointments.service import AppointmentService
from domains.appointments.repository import AppointmentRepository
from shared.schemas import ErrorDetail

router = APIRouter(tags=["Appointments"])


@router.post(
    "",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorDetail},
        403: {"model": ErrorDetail},
        409: {"model": ErrorDetail},
    },
)
async def create_appointment(
    payload: AppointmentCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppointmentRead:
    service = AppointmentService(AppointmentRepository(db))
    try:
        appointment = await service.create(payload, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return AppointmentRead.model_validate(appointment)
```

## Schema-First Design

1. Define request schema in `domains/{domain}/schemas.py`
2. Define response schema (separate from request if needed)
3. Import schemas in the router — never use raw dicts
4. Use `response_model` on every endpoint

```python
# Request schema — only fields the client sends
class AppointmentCreate(BaseModel):
    service_id: UUID
    scheduled_time: datetime
    client_lat: float
    client_lng: float

# Response schema — includes server-generated fields
class AppointmentRead(BaseModel):
    id: UUID
    status: AppointmentStatus
    estimated_price: int  # cents
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

## Auth Patterns

```python
from app.core.auth import get_current_user, require_role

# Basic JWT auth
async def endpoint(current_user = Depends(get_current_user)):

# Role-based auth
async def detailer_only(user = Depends(require_role("detailer"))):

# Both combined
async def create(
    payload: AppointmentCreate,
    current_user = Depends(get_current_user),
):
    if current_user.role != "client":
        raise HTTPException(403, "Only clients can book")
```

## Error Response Format

Always use `ErrorDetail` from `shared.schemas`:

```python
from shared.schemas import ErrorDetail

raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail=ErrorDetail(
        code="ALREADY_BOOKED",
        message="This time slot is no longer available.",
    ).model_dump(),
)
```

**Never return raw strings** like `{"detail": "error"}`.

## Audit Logging

Log every mutation:

```python
from domains.audit.repository import AuditRepository
from domains.audit.models import AuditAction

await AuditRepository(db).log(
    action=AuditAction.APPOINTMENT_CREATED,
    entity_type="appointment",
    entity_id=str(appointment.id),
    actor_id=current_user.id,
    metadata={"service_id": str(payload.service_id)},
)
```

## Rate Limiting

Apply rate limits on auth and mutation endpoints:

```python
from app.core.limiter import limiter
from fastapi import Request

@router.post("/auth/token", dependencies=[Depends(limiter.limit("10/minute"))])
```

## Anti-Patterns

```python
# ❌ BAD: Raw dict response, no schema
return {"id": str(appointment.id), "status": appointment.status}

# ✅ GOOD: Schema-validated response
return AppointmentRead.model_validate(appointment)

# ❌ BAD: Returning raw string error
raise HTTPException(400, "Invalid time slot")

# ✅ GOOD: Typed error detail
raise HTTPException(400, ErrorDetail(code="INVALID_SLOT", message="...").model_dump())

# ❌ BAD: Including router directly in main.py
from app.routers.appointment_router import router
app.include_router(router)  # ❌ bypasses api/router.py

# ✅ GOOD: Aggregated in api/router.py
api_router.include_router(appointments_router)

# ❌ BAD: No response codes documented
@router.post("/appointments")

# ✅ GOOD: Full response documentation
@router.post("", response_model=AppointmentRead, status_code=201,
            responses={409: {"model": ErrorDetail}})
```

## Success Criteria

- Endpoint visible in Swagger `/docs`
- All error codes documented with `responses={}`
- Auth applied via `Depends(get_current_user)`
- Audit log on every mutation
- Schema used for both request and response
- Path follows `/api/v1/{plural}` convention