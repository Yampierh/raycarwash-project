---
name: backend-repository-pattern
description: Data access layer patterns for SQLAlchemy async backends. Use when creating or modifying repositories. Covers soft deletes, advisory locks, session management, and base class patterns.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - failure_modes
preconditions:
  - All queries filter is_deleted == False
  - Advisory lock used for booking race conditions
outputs:
  - Repository class with typed methods
  - Soft delete methods
  - Pagination support
conflicts:
  - Never return Row objects (must be typed Model)
  - Never use query() style (use select())
  - Never hard-delete
execution_priority: 2
---

# Repository Pattern

**Priority: CRITICAL**  
**Applies to:** Data access layer, repository creation, query modification

## Domain Structure

```
domains/{domain}/
├── models.py      # SQLAlchemy models
├── repository.py  # Data access
├── service.py
├── router.py
└── schemas.py
```

## Base Repository

Create a base class in `infrastructure/db/`:

```python
# infrastructure/db/base_repository.py
from typing import TypeVar, Generic, Type
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.db.base import Base

Model = TypeVar("Model", bound=Base)


class BaseRepository(Generic[Model]):
    model: Type[Model]

    def __init__(self, db: AsyncSession):
        self._db = db

    def _base_query(self):
        """Default: exclude soft-deleted rows."""
        return select(self.model).where(self.model.is_deleted == False)

    async def get_by_id(self, id: UUID) -> Model | None:
        q = self._base_query().where(self.model.id == id)
        result = await self._db.execute(q)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100) -> list[Model]:
        q = self._base_query().limit(limit)
        result = await self._db.execute(q)
        return list(result.scalars().all())

    async def save(self, entity: Model) -> Model:
        self._db.add(entity)
        await self._db.flush()
        await self._db.refresh(entity)
        return entity

    async def soft_delete(self, id: UUID) -> None:
        await self._db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(
                is_deleted=True,
                deleted_at=func.now() if self._db.bind else None,
            )
        )
```

## Standard Repository Template

```python
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from domains.appointments.models import Appointment, AppointmentStatus
from domains.appointments.repository import AppointmentRepository

class AppointmentRepository(BaseRepository[Appointment]):
    model = Appointment

    async def find_active_by_detailer(
        self,
        detailer_id: UUID,
        from_time: datetime | None = None,
    ) -> list[Appointment]:
        q = (
            select(Appointment)
            .where(
                Appointment.detailer_id == detailer_id,
                Appointment.is_deleted == False,
                Appointment.status.in_([
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS,
                    AppointmentStatus.ARRIVED,
                ]),
            )
            .order_by(Appointment.scheduled_time)
        )
        if from_time:
            q = q.where(Appointment.scheduled_time >= from_time)
        result = await self._db.execute(q)
        return list(result.scalars().all())

    async def find_by_id_with_lock(self, id: UUID) -> Appointment | None:
        """Use pg_advisory_xact_lock for booking race conditions."""
        from sqlalchemy import text
        await self._db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int(hash(str(id)))},
        )
        q = select(Appointment).where(
            Appointment.id == id,
            Appointment.is_deleted == False,
        )
        result = await self._db.execute(q)
        return result.scalar_one_or_none()

    async def find_by_client(
        self,
        client_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Appointment], int]:
        base = (
            select(Appointment)
            .where(
                Appointment.client_id == client_id,
                Appointment.is_deleted == False,
            )
            .order_by(Appointment.created_at.desc())
        )
        count_q = select(func.count()).select_from(base.subquery())
        count_result = await self._db.execute(count_q)
        total = count_result.scalar() or 0
        q = base.limit(limit).offset(offset)
        result = await self._db.execute(q)
        return list(result.scalars().all()), total
```

## Advisory Lock Pattern

Use for critical sections where race conditions cause data corruption:

```python
# Booking creation — prevents double-booking the same detailer
async def create_booking(self, appointment: Appointment) -> Appointment:
    await self._db.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": int(hash(str(appointment.detailer_id)))}
    )
    # Now safe to check availability and insert
    available = await self._check_availability(appointment.detailer_id, appointment.scheduled_time)
    if not available:
        raise SlotUnavailableError()
    self._db.add(appointment)
    await self._db.flush()
    await self._db.refresh(appointment)
    return appointment
```

## Pagination Pattern

```python
async def list_with_pagination(
    self,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Model], int]:
    # Count query
    count_q = select(func.count()).select_from(
        self._base_query().subquery()
    )
    count_result = await self._db.execute(count_q)
    total = count_result.scalar() or 0

    # Data query
    data_q = (
        self._base_query()
        .order_by(self.model.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await self._db.execute(data_q)
    return list(result.scalars().all()), total
```

## Index Checklist for Every Model

Every table needs indexes on:

```python
__table_args__ = (
    Index("ix_appointments_detailer_scheduled", "detailer_id", "scheduled_time", "is_deleted"),
    Index("ix_appointments_client_created", "client_id", "created_at"),
    Index("ix_appointments_status", "status", "is_deleted"),
)
```

## Session Management Rules

| Rule | Reason |
|------|--------|
| All methods `async` | Non-blocking I/O |
| Use `select()` not `query()` | Modern SQLAlchemy 2.0 style |
| Call `flush()` after mutations | Flushes to DB, keeps transaction open |
| Call `refresh()` after creates | Loads DB-generated fields (UUID, timestamps) |
| Caller owns `commit()` | Services/routers commit atomically |

## Anti-Patterns

```python
# ❌ BAD: query() style — deprecated
results = session.query(Appointment).filter_by(detailer_id=id).all()

# ✅ GOOD: select() style
q = select(Appointment).where(Appointment.detailer_id == id)
result = await db.execute(q)

# ❌ BAD: Returning Row objects
return result.rows  # no type safety

# ✅ GOOD: Typed model list
return list(result.scalars().all())

# ❌ BAD: No soft delete filter
q = select(Appointment).where(Appointment.detailer_id == id)
# Also matches deleted rows!

# ✅ GOOD: Always filter is_deleted
q = (
    select(Appointment)
    .where(Appointment.detailer_id == id)
    .where(Appointment.is_deleted == False)
)

# ❌ BAD: No advisory lock on critical race section
await self._db.add(appointment)
await self._db.flush()
# Two concurrent requests both succeed → double booking

# ✅ GOOD: Lock first
await self._db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})

# ❌ BAD: Missing refresh after create
self._db.add(entity)
await self._db.flush()
return entity  # UUID, timestamps not loaded

# ✅ GOOD: Refresh to load DB-generated fields
self._db.add(entity)
await self._db.flush()
await self._db.refresh(entity)
return entity
```

## Success Criteria

- All queries filter `is_deleted == False` by default
- Advisory lock used for booking race conditions
- `pg_refresh()` called after every create
- All methods are async
- Return types are `Model | None` or `list[Model]`
- Indexes defined on all FK and filter columns