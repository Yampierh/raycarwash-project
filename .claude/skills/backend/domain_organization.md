---
name: backend-domain-organization
description: Domain-driven design patterns for this codebase. Use when organizing code into domains or creating new domains. Covers domain structure, cross-domain communication, and the domains/ vs app/ split.
depends_on:
  - architecture_orchestrator
  - system_contracts
preconditions:
  - New domains go in domains/{name}/
  - Models registered in infrastructure/db/registry.py
outputs:
  - New domain directory structure
  - Router aggregated via api/router.py
conflicts:
  - Domain layer never imports FastAPI (app/)
  - Domain service never imports other domain services
  - Shared schemas never in domains/ (go in shared/)
execution_priority: 2
---

# Domain Organization

**Priority: HIGH**  
**Applies to:** New domain creation, architecture decisions, cross-domain design

## Directory Structure

```
backend/
├── domains/                    # Pure domain logic
│   ├── auth/
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── repository.py      # Data access
│   │   ├── service.py        # Business logic
│   │   ├── router.py         # API endpoints
│   │   ├── schemas.py        # Pydantic schemas
│   │   └── __init__.py
│   ├── users/
│   ├── providers/            # Detailers
│   ├── vehicles/
│   ├── appointments/
│   ├── payments/
│   ├── matching/
│   ├── reviews/
│   ├── services_catalog/
│   ├── audit/
│   ├── realtime/
│   └── __init__.py
├── app/                      # Application infrastructure
│   ├── core/                 # Config, auth, limiter
│   ├── db/                   # Session, seed, registry
│   ├── repositories/        # Legacy repos (migrating to domains/)
│   ├── services/            # Legacy services (migrating)
│   ├── routers/             # Legacy routers (migrating)
│   ├── schemas/             # Shared schemas (ErrorDetail, etc.)
│   ├── workers/            # Background tasks
│   └── ws/                 # WebSocket connection manager
├── infrastructure/           # Infrastructure concerns
│   ├── db/                  # Base, session, registry
│   └── redis/               # Redis client
├── shared/                  # Cross-domain schemas
│   └── schemas.py
├── api/
│   └── router.py            # Aggregates all domain routers
└── main.py
```

## Domain Design Rules

### What goes in `domains/`

- SQLAlchemy models (`models.py`)
- Repository classes (`repository.py`)
- Service classes (`service.py`)
- Router endpoints (`router.py`)
- Pydantic schemas (`schemas.py`)

**Pure domain logic only.** No FastAPI imports, no middleware.

### What goes in `app/`

- FastAPI-specific: config, auth dependencies, rate limiter
- Seed scripts
- Background workers
- WebSocket connection manager

### What goes in `shared/`

- `ErrorDetail` schema
- `HealthResponse` schema
- Any schema used across multiple domains

## Cross-Domain Communication

**Never import one domain's service into another domain's service.**

```python
# ❌ BAD: Cross-domain service import
from domains.payments.service import PaymentService

class AppointmentService:
    def __init__(self, ...):
        self._payment = PaymentService(...)
    async def complete(self, appt):
        await self._payment.capture(appt)

# ✅ GOOD: Domain events via audit or realtime
from domains.realtime.service import RealtimeService
from domains.audit.repository import AuditRepository

async def complete(self, appt, db):
    async with db.begin():
        appt.status = AppointmentStatus.COMPLETED
        await self._repo.save(appt)
        await AuditRepository(db).log(AuditAction.APPOINTMENT_COMPLETED, ...)
        await RealtimeService(db).emit_status_update(appt)
```

**Reason:** Cross-domain service imports create circular dependencies and tight coupling. Events decouple domains.

## Creating a New Domain

### Step 1: Create directory structure

```
domains/newdomain/
├── models.py
├── repository.py
├── service.py
├── router.py
├── schemas.py
└── __init__.py
```

### Step 2: Define models

```python
# domains/newdomain/models.py
from __future__ import annotations
from infrastructure.db.base import Base, TimestampMixin
from sqlalchemy import String, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class NewEntity(TimestampMixin, Base):
    __tablename__ = "new_entities"
    __table_args__ = (
        Index("ix_new_entities_owner", "owner_id", "is_deleted"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Step 3: Register in infrastructure/db/registry

```python
# infrastructure/db/registry.py
from domains.newdomain.models import NewEntity
# ... other imports

__all__ = [
    # ...
    NewEntity,
]
```

### Step 4: Create router and aggregate

```python
# domains/newdomain/router.py
from fastapi import APIRouter

router = APIRouter(tags=["NewDomain"])
```

```python
# api/router.py
from domains.newdomain.router import router as newdomain_router
api_router.include_router(newdomain_router)
```

## Domain Naming Conventions

| Domain | Table prefix | Key entity |
|--------|-------------|-----------|
| `auth` | `auth_` | User, Role, RefreshToken |
| `users` | `users` | User |
| `providers` | `providers` | Provider (Detailer) |
| `vehicles` | `vehicles` | Vehicle |
| `appointments` | `appointments` | Appointment |
| `payments` | `payment_` | PaymentLedger |
| `matching` | — | (no DB model) |
| `reviews` | `reviews` | Review |
| `services_catalog` | `services` | Service, Addon |
| `audit` | `audit_` | AuditLog |

## Anti-Patterns

```python
# ❌ BAD: FastAPI imports in domain model
from fastapi import HTTPException  # no

# ✅ GOOD: Pure Python domain
from uuid import UUID

# ❌ BAD: Cross-domain service dependency
from domains.payments.service import PaymentService
# Creates circular import risk

# ✅ GOOD: Event-based decoupling
await RealtimeService(db).emit_event(...)

# ❌ BAD: Storing schema in domain
# schemas.py in domains/ — only schemas for this domain

# ✅ GOOD: Shared schemas in shared/
from shared.schemas import ErrorDetail
```

## Success Criteria

- New domains created in `domains/` directory
- Models registered in `infrastructure/db/registry.py`
- Routers aggregated via `api/router.py`
- No FastAPI imports in domain layer
- No cross-domain service imports
- Cross-domain communication via events/audit