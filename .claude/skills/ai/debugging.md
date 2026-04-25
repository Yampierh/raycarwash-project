---
name: ai-debugging
description: Systematic debugging across FastAPI backend layers. Use when diagnosing crashes, 500 errors, unexpected behavior, or test failures. Follows the symptom → root cause → fix → verify cycle.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - failure_modes
  - infra-observability
preconditions:
  - X-Request-ID available in all logs
  - Failure mode identified before fix
outputs:
  - Root cause localized to layer
  - Fix applied at root cause
  - Regression test added
conflicts:
  - Never fix symptom without identifying root cause
  - Never skip failure_modes review
execution_priority: 4
---

# Debugging the Backend

**Priority: CRITICAL**  
**Applies to:** Bug diagnosis, error investigation, test failures, runtime crashes

## Debugging Cycle

```
Symptom → Narrow → Hypothesize → Fix → Verify → Done
```

## Step 1: Collect Symptoms

Ask:
1. What error code? (400, 404, 409, 500, 502?)
2. What does the response body say?
3. What is in the server logs? (search by `X-Request-ID`)
4. Does it fail in Swagger but work with curl?
5. Does it fail for all users or just some?

## Step 2: Narrow the Layer

Use the call chain to localize:

```
Router → Service → Repository → SQLAlchemy → DB
  ↓          ↓          ↓            ↓
Schema   Business    Query        Constraint
mismatch  logic      syntax        error
```

### Schema Mismatch (500 on client)

Check if model and schema are in sync:

```python
# Model
class Appointment(Base):
    new_field: Mapped[str] = mapped_column(String(100))

# Schema — forgot to add new_field
class AppointmentRead(BaseModel):
    id: UUID
    # new_field is missing → 500
```

**Fix:** Add missing field to schema.

### Business Logic Error (409, 403)

Check service validation:

```python
# User hit business rule
raise HTTPException(409, "Slot not available")
```

Check logs for the full stack trace.

### Query Error (500 in logs)

Check repository SQL:

```python
# Check the actual SQL being generated
result = await db.execute(q)
# If error: psycopg2.errors.UndefinedColumn
# The model has the field but the DB doesn't (migration missing)
```

**Fix:** Run `alembic revision --autogenerate` + `alembic upgrade head`.

### Constraint Error (IntegrityError)

PostgreSQL unique/ FK violation. Caught by global handler → returns 409.

## Step 3: Common Issues

### 500 on appointment creation

| Check | Command |
|-------|---------|
| Model field added? | `alembic upgrade head` |
| Schema matches model? | Compare `Appointment` model vs `AppointmentRead` schema |
| `estimated_price` set? | Service calculates and sets price |
| Advisory lock? | `SELECT pg_advisory_xact_lock` in repository |

### 401 Unauthorized

| Check | Command |
|-------|---------|
| Token expired? | JWT `exp` claim |
| Token valid signature? | `decode_token()` |
| Header format? | `Authorization: Bearer <token>` |

### 403 Forbidden

| Check | Command |
|-------|---------|
| Role check in router? | `require_role("detailer")` |
| `VALID_TRANSITIONS` for status? | Role not in allowed set |
| Same user accessing own resource? | Check `actor_id == current_user.id` |

### Webhook 400

| Check | Command |
|-------|---------|
| Signature verification? | `Webhook.construct_event()` |
| Idempotency check? | `processed_webhooks` table |
| Event type handled? | Add to `handle_stripe_event()` |

### Worker crash loop

Check worker error handling:

```python
# Worker catches but logs and retries
except Exception:
    logger.error("Worker error: %s", exc)
    await asyncio.sleep(5)
# If error persists → backoff needed
```

## Step 4: Reproduce Locally

```bash
# Start backend
npm run dev:backend

# Test endpoint
curl -X POST http://localhost:8000/api/v1/appointments \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"service_id": "..."}'

# Check Swagger
http://localhost:8000/docs
```

## Step 5: Fix and Verify

1. Fix the root cause, not the symptom
2. Write a test that catches the bug
3. Run `pytest`
4. Verify in Swagger

## Anti-Patterns

```python
# ❌ BAD: Random log to debug
print("here")  # No structured context
logger.debug("here")  # Better but no request_id

# ✅ GOOD: Structured log with request context
logger.info("Booking failed", extra={
    "request_id": request_id_var.get(),
    "slot_id": str(slot_id),
})

# ❌ BAD: Comment out code to test
# appointment.save()  # What?

# ✅ GOOD: Write a failing test first
def test_appointment_creates_with_estimated_price():
    appt = await service.create(...)
    assert appt.estimated_price > 0
```

## Debugging Checklist

```
□ Error code identified → 4xx or 5xx?
□ X-Request-ID found in logs?
□ Layer narrowed → schema / service / repo / DB?
□ Root cause identified?
□ Fix applied at the root cause layer?
□ Test added to catch the bug?
□ pytest passes?
□ Swagger verified?
```

## Success Criteria

- `X-Request-ID` traced through all log lines
- Root cause localized to a specific layer
- Fix applied at the root cause (not symptom)
- Test added that would have caught the bug
- `pytest` passes
- Regression prevented