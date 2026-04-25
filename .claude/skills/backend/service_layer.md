---
name: backend-service-layer
description: Service layer patterns for FastAPI + DDD backends. Use when writing or refactoring business logic. Services own transactions, domain rules, and event emission — never SQL or HTTP calls.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - repository_pattern
  - state_machine
  - failure_modes
preconditions:
  - system_contracts loaded (appointment/payment lifecycle understood)
  - Repository methods exist before service calls them
outputs:
  - Service class with business logic
  - Transactional mutations
  - Audit log calls inside transactions
conflicts:
  - Service never contains SQL (belongs in repository)
  - Service never makes HTTP calls (belongs in workers/clients)
  - Service never commits outside of db.begin() transaction
  - Service never imports other domain services
execution_priority: 2
---

# Service Layer Design

**Priority: CRITICAL**  
**Applies to:** Writing or refactoring services, business logic implementation

## Service Responsibilities

Services own:
- **Business logic** — validation, calculations, state transitions
- **Transaction management** — wrapping reads + writes atomically
- **Event emission** — sending domain events or audit logs
- **Orchestration** — coordinating multiple repositories

Services do **NOT** own:
- SQL queries (→ repository)
- HTTP calls (→ clients/workers)
- Direct DB commits outside transactions
- Schema serialization (→ routers)

## Placement

```
domains/{domain}/
├── models.py
├── repository.py
├── service.py      ← One service per domain
├── router.py
└── schemas.py
```

## Standard Pattern

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from domains.appointments.repository import AppointmentRepository
from domains.appointments.models import Appointment
from domains.audit.repository import AuditRepository
from domains.audit.models import AuditAction


class AppointmentService:
    def __init__(self, repo: AppointmentRepository, audit_repo: AuditRepository):
        self._repo = repo
        self._audit = audit_repo

    async def create(self, payload: AppointmentCreate, client_id: UUID) -> Appointment:
        # 1. Validate business rules
        await self._validate_booking(payload, client_id)

        # 2. Create model instance
        appointment = Appointment(
            client_id=client_id,
            detailer_id=payload.detailer_id,
            service_id=payload.service_id,
            scheduled_time=payload.scheduled_time,
            estimated_price=self._calculate_price(payload),
        )

        # 3. Transaction: save + audit log
        async with self._repo._db.begin():
            saved = await self._repo.save(appointment)
            await self._audit.log(
                action=AuditAction.APPOINTMENT_CREATED,
                entity_type="appointment",
                entity_id=str(saved.id),
                actor_id=client_id,
            )
        return saved

    async def update_status(
        self,
        appointment_id: UUID,
        new_status: AppointmentStatus,
        actor_id: UUID,
        role: str,
    ) -> Appointment:
        appointment = await self._repo.get_by_id(appointment_id)
        if not appointment:
            raise ValueError("Appointment not found")

        # 4. Validate state machine transition
        current_status = appointment.status
        allowed = VALID_TRANSITIONS.get(current_status, {}).get(new_status)
        if not allowed or role not in allowed:
            raise PermissionError(f"Transition {current_status} → {new_status} not allowed for {role}")

        # 5. Apply transition + side effects
        appointment.status = new_status
        self._stamp_timestamp(appointment, new_status)

        # 6. Transaction
        async with self._repo._db.begin():
            updated = await self._repo.save(appointment)
            await self._audit.log_status_change(updated, actor_id)

        return updated
```

## Transaction Pattern

**Always use explicit transaction blocks.** Never call `db.commit()` directly.

```python
# ✅ GOOD: Atomic transaction
async with db.begin():
    result = await self._repo.save(entity)
    await self._audit.log(...)

# ❌ BAD: Auto-commit outside transaction
await self._repo.save(entity)       # auto-commits
await self._audit.log(...)        # separate transaction — non-atomic
```

## Service-to-Service Communication

**Never call other services directly.** Use domain events or the worker system.

```python
# ❌ BAD: Tight coupling
detailer_service = DetailerService(detailer_repo)
await detailer_service.update_location(detailer_id, lat, lng)

# ✅ GOOD: Domain event
from domains.realtime.service import RealtimeService

async with db.begin():
    await self._repo.save(appointment)
    await RealtimeService(db).emit_appointment_created(appointment)
```

## Error Handling

```python
class AppointmentNotFoundError(Exception):
    pass

class InvalidTransitionError(Exception):
    pass

async def get_appointment(self, id: UUID) -> Appointment:
    appt = await self._repo.get_by_id(id)
    if not appt:
        raise AppointmentNotFoundError(f"Appointment {id} not found")
    return appt
```

Routers catch service exceptions:

```python
try:
    appt = await service.create(payload, client_id)
except AppointmentNotFoundError as e:
    raise HTTPException(404, str(e))
except InvalidTransitionError as e:
    raise HTTPException(403, str(e))
```

## Anti-Patterns

```python
# ❌ BAD: SQL in service
async def get_appointments(self, detailer_id: UUID):
    result = await self._db.execute(
        text("SELECT * FROM appointments WHERE detailer_id = :id"),
        {"id": str(detailer_id)}
    )
    # SQL belongs in repository

# ✅ GOOD: Repository query
async def get_appointments(self, detailer_id: UUID):
    return await self._repo.find_by_detailer(detailer_id)

# ❌ BAD: HTTP call in service
async def notify_client(self, appointment: Appointment):
    async with httpx.AsyncClient() as client:
        await client.post(f"{APP_BASE_URL}/notify", json={...})

# ✅ GOOD: Emit event for worker to handle
await RealtimeService(self._db).emit_status_update(appointment)

# ❌ BAD: Commit outside transaction
async def create(self, payload):
    appointment = Appointment(...)
    await self._repo.save(appointment)
    await self._db.commit()  # redundant

# ✅ GOOD: Atomic
async with self._db.begin():
    await self._repo.save(appointment)
```

## Service Size Rule

If a service exceeds **200 lines**, split it:

- Extract calculation logic into a dedicated calculator/fare service
- Extract notification logic into an event emitter
- Extract state machine logic into a dedicated transition service

## Success Criteria

- Service has no `text()`, `execute()`, or raw SQL
- Service has no standalone `commit()` calls
- Service has no `httpx` or `aiohttp` HTTP calls
- All mutations wrapped in `async with db.begin()`
- All mutations emit audit logs inside the transaction
- Service errors are typed custom exceptions