---
name: backend-refactor
description: Safe refactoring patterns for FastAPI + DDD-lite backends. Use when modifying repositories, services, routers, models, or workers. Follows the Router → Service → Repository → Model call chain.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - failure_modes
  - repository_pattern
  - state_machine
preconditions:
  - system_contracts loaded (lifecycles understood)
  - No violation of immutability hierarchy
outputs:
  - Modified router, service, repository, or model
  - Updated schema
  - Passing pytest
conflicts:
  - Never modify estimated_price post-creation
  - Never bypass repository with raw SQL
  - Never hard-delete rows
execution_priority: 2
---

# Safe Backend Refactoring

**Priority: CRITICAL**  
**Applies to:** Backend task, code modification, refactoring, adding endpoints

## When to Use

- Adding a field to an existing model
- Changing repository query logic
- Modifying service business logic
- Creating or updating a router endpoint
- Updating Pydantic schemas
- Adding or modifying background workers
- Any task touching the data layer

## Step-by-Step Process

### Phase 1 — Understand First (Never Skip)

1. **Trace the full call chain** before touching anything:
   ```
   Router → Service → Repository → SQLAlchemy Model → DB Schema
   ```
2. **Read in order:** `domains/{domain}/models.py` → `repository.py` → `service.py` → `router.py` → `schemas.py`
3. **Identify the contract** — what does the router return? What does the service accept? Changing the schema contract requires updating all callers.

### Phase 2 — Make Changes Bottom-Up

4. **Model first** — add the column, index, or enum value
5. **Repository** — update the query or mutation
6. **Service** — update business logic
7. **Router** — update endpoint, add new response codes
8. **Schema** — mirror model changes in Pydantic schemas

### Phase 3 — Verify

9. **Run seed functions** — model changes may break seed scripts
10. **Run tests** — `pytest` must pass
11. **Check the API** — use Swagger `/docs` to verify response shape

## Critical Rules

| Rule | Why |
|------|-----|
| `estimated_price` is immutable after appointment creation | Financial consistency — changing it breaks the ledger |
| Prices are always in **cents** (int) | Float precision breaks financial calculations |
| All timestamps are UTC | Never convert to local time in the DB layer |
| Never hard-delete | Use `is_deleted=True` + `deleted_at` — audit trail depends on it |
| Never bypass repository with raw SQL | Breaks the DDD layer contract |
| Schema must mirror model | Mismatch causes 500 errors on the client |
| Advisory lock on appointment booking | Prevents double-booking race conditions |

## Repository Bottom-Up Checklist

```
□ Model changed?     → Update schema
□ Schema changed?    → Update service return types
□ Service changed?   → Update router handlers
□ Router changed?    → Update tests + Swagger docs
□ Tests updated?     → Run pytest
```

## Anti-Patterns

```python
# ❌ BAD: Mutating estimated_price after creation
appointment.estimated_price = new_calculated_price
await db.commit()

# ✅ GOOD: Only set actual_price on COMPLETED
if target_status == AppointmentStatus.COMPLETED:
    appointment.actual_price = final_amount

# ❌ BAD: Hard delete bypasses audit trail
await db.execute(delete(Appointment).where(...))

# ✅ GOOD: Soft delete preserves history
await db.execute(
    update(Appointment)
    .where(Appointment.id == id)
    .values(is_deleted=True, deleted_at=utcnow())
)

# ❌ BAD: Raw SQL in service breaks layer isolation
result = await db.execute(text(f"SELECT * FROM appointments WHERE ..."))

# ✅ GOOD: Repository owns all SQL
appointments = await self._repo.find_active_by_detailer(detailer_id)

# ❌ BAD: No advisory lock on booking race condition
# (Two concurrent requests could book the same detailer)

# ✅ GOOD: Advisory lock at transaction start
await db.execute(
    text("SELECT pg_advisory_xact_lock(:key)"),
    {"key": int(hash(str(detailer_id)))}
)
```

## Success Criteria

- `pytest` passes with no modifications to existing tests
- API response shape unchanged (unless explicitly requested)
- No raw SQL introduced in service or router layers
- Soft delete patterns applied everywhere
- `estimated_price` never mutated post-creation