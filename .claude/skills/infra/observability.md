---
name: infra-observability
description: Logging, tracing, and observability patterns. Use when debugging issues, adding metrics, or configuring log levels. Mandatory logging contract for all domains.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - failure_modes
preconditions:
  - request_id propagation enforced on every request
  - Structured JSON format configured in main.py
outputs:
  - Structured JSON logs with request_id in every line
  - Audit log entries for all mutations
  - Worker heartbeat logs
conflicts:
  - Never log PII or sensitive data
  - Never use print() instead of structured logger
  - Never log without request_id context
execution_priority: 3
---

# Observability

**Priority: HIGH**  
**Applies to:** Logging, correlation IDs, metrics, debugging

## Logging Structure

RayCarWash uses structured JSON logging:

```python
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(service)s %(env)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    rename_fields={"levelname": "level", "asctime": "timestamp"},
))
_log_handler.addFilter(RequestIdFilter())
_log_handler.addFilter(StaticFieldsFilter(service="raycarwash-backend", env=env))
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])
```

## Correlation ID

Every request carries an `X-Request-ID`:

```python
# Middleware injects request_id_var
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_var.reset(token)
```

Log with request context:

```python
logger.info(
    "Appointment created",
    extra={
        "appointment_id": str(appointment.id),
        "detailer_id": str(detailer_id),
        "request_id": request_id_var.get(),
    },
)
```

## Log Levels

| Level | Use |
|-------|-----|
| `DEBUG` | Detailed diagnostic info (dev only) |
| `INFO` | Normal operation events |
| `WARNING` | Recoverable issues (e.g., rate limit hit) |
| `ERROR` | Unhandled exceptions, failed operations |
| `CRITICAL` | Service unavailable |

## Key Events to Log

```python
# Auth
INFO: "User login", "User registered", "Password reset requested"
WARNING: "Failed login attempt"
ERROR: "Token validation failed"

# Appointments
INFO: "Appointment created", "Status changed", "Detailer assigned"
WARNING: "Detailer went offline"
ERROR: "Status transition failed"

# Payments
INFO: "Payment captured", "Refund issued"
ERROR: "Webhook signature failed", "Stripe API error"

# Workers
INFO: "Worker started", "Worker stopped"
ERROR: "Worker loop error"
```

## Audit Log Events

All mutations logged via `AuditRepository`:

```python
from domains.audit.models import AuditAction

AUDIT_ACTION_NAMES = {
    AuditAction.USER_REGISTERED: "user_registered",
    AuditAction.APPOINTMENT_CREATED: "appointment_created",
    AuditAction.APPOINTMENT_STATUS_CHANGED: "appointment_status_changed",
    AuditAction.PAYMENT_CAPTURED: "payment_captured",
    AuditAction.REFUND_ISSUED: "refund_issued",
    AuditAction.REVIEW_SUBMITTED: "review_submitted",
}
```

## Metrics (Production)

Track these metrics per deployment:

| Metric | Description |
|--------|------------|
| `request_count` | Total requests by endpoint + status |
| `request_latency_p99` | 99th percentile response time |
| `db_pool_active` | Active DB connections |
| `db_pool_idle` | Idle DB connections |
| `ws_active_connections` | Active WebSocket connections |
| `worker_errors` | Worker loop errors per minute |
| `webhook_failures` | Failed Stripe webhook verifications |

## Anti-Patterns

```python
# ❌ BAD: print() instead of logger
print("User logged in")  # No structured format

# ✅ GOOD: Structured logging
logger.info("User logged in", extra={"user_id": str(user.id)})

# ❌ BAD: No error details
logger.error("Request failed")

# ✅ GOOD: Full exception context
logger.error("Database query failed", extra={"query": sql}, exc_info=True)

# ❌ BAD: Logging sensitive data
logger.info("Payment", extra={"card_number": card_number})

# ✅ GOOD: Never log PII or payment details
logger.info("Payment processed", extra={"amount_cents": amount_cents})
```

## Structured Logging Contract

### JSON Schema (Production Mandatory)

Every log line MUST follow this schema:

```json
{
  "timestamp": "2026-04-25T10:30:00.000Z",
  "level": "INFO",
  "name": "raycarwash.appointments",
  "message": "Appointment created",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "service": "raycarwash-backend",
  "env": "production",
  "appointment_id": "...",
  "client_id": "...",
  "detailer_id": "..."
}
```

### Log Format Configuration

```python
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(service)s %(env)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    rename_fields={"levelname": "level", "asctime": "timestamp"},
))
_log_handler.addFilter(RequestIdFilter())
_log_handler.addFilter(StaticFieldsFilter(service="raycarwash-backend", env=env))
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])
```

## Request ID Propagation Contract

**Rule: Every async task inherits the request_id of its parent request.**

```
HTTP request (middleware sets request_id_var)
    │
    ├── Router handler reads request_id_var.get()
    │       └── Logs with request_id in extra
    │
    ├── Service → Repository → DB (request_id in context)
    │
    ├── Audit log → stored with request_id in metadata
    │
    └── Worker emits → request_id in WS message payload
```

**Implementation:**

```python
# Middleware: every request gets or generates X-Request-ID
request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
token = request_id_var.set(request_id)
try:
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
finally:
    request_id_var.reset(token)
```

**Worker context propagation:**

```python
# Workers receive request_id from Redis message or app state
async def location_worker(app_state):
    while True:
        locations = await _fetch_active_locations(app_state.db)
        await app_state.ws_manager.broadcast_locations(
            locations,
            trace_id=request_id_var.get(),  # Propagate to WS
        )
        await asyncio.sleep(INTERVAL)
```

## Cross-Service Trace Rules

### Log Every Lifecycle Transition

```python
# Appointment lifecycle trace
logger.info(
    "Appointment lifecycle transition",
    extra={
        "request_id": request_id_var.get(),
        "appointment_id": str(appointment.id),
        "from_status": old_status,
        "to_status": new_status,
        "actor_id": str(actor_id),
        "role": role,
        "layer": "service",
    },
)
```

### WebSocket Correlation

Every WS message MUST carry the trace:

```python
await ws_manager.send_to_room(
    f"appt:{appointment_id}",
    {
        "type": "status_update",
        "request_id": request_id_var.get(),
        "trace_id": request_id_var.get(),  # Alias for compatibility
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "status": new_status.value,
        },
    },
)
```

### Worker + WS Cross-Correlation

```
Worker loop iteration
    │
    ├── Log: "Worker iteration" (INFO, every N iterations)
    ├── Log: "Worker error" (ERROR, on failure)
    │
    └── WS event: trace_id set from worker context
```

Worker heartbeat log:

```python
ITERATION = 0
async def location_worker(app_state):
    global ITERATION
    while True:
        try:
            await asyncio.sleep(INTERVAL)
            ITERATION += 1
            if ITERATION % 100 == 0:  # Log every 100 iterations
                logger.info(
                    "Worker heartbeat",
                    extra={
                        "worker": "location",
                        "iteration": ITERATION,
                        "active_rooms": len(app_state.ws_manager._rooms),
                    },
                )
            await do_work(app_state)
        except asyncio.CancelledError:
            logger.info("Worker shutdown", extra={"worker": "location"})
            break
        except Exception as exc:
            logger.error(
                "Worker error",
                extra={"worker": "location", "error": str(exc)},
                exc_info=True,
            )
```

## Audit Log Events

All mutations logged via `AuditRepository`:

```python
from domains.audit.models import AuditAction

AUDIT_ACTION_NAMES = {
    AuditAction.USER_REGISTERED: "user_registered",
    AuditAction.APPOINTMENT_CREATED: "appointment_created",
    AuditAction.APPOINTMENT_STATUS_CHANGED: "appointment_status_changed",
    AuditAction.PAYMENT_CAPTURED: "payment_captured",
    AuditAction.REFUND_ISSUED: "refund_issued",
    AuditAction.REVIEW_SUBMITTED: "review_submitted",
}
```

## Metrics (Production)

Track these metrics per deployment:

| Metric | Description |
|--------|------------|
| `request_count` | Total requests by endpoint + status |
| `request_latency_p99` | 99th percentile response time |
| `db_pool_active` | Active DB connections |
| `db_pool_idle` | Idle DB connections |
| `ws_active_connections` | Active WebSocket connections |
| `worker_errors` | Worker loop errors per minute |
| `webhook_failures` | Failed Stripe webhook verifications |

## Anti-Patterns

```python
# ❌ BAD: print() instead of logger
print("User logged in")  # No structured format

# ✅ GOOD: Structured logging
logger.info("User logged in", extra={"user_id": str(user.id)})

# ❌ BAD: No error details
logger.error("Request failed")

# ✅ GOOD: Full exception context
logger.error("Database query failed", extra={"query": sql}, exc_info=True)

# ❌ BAD: Logging sensitive data
logger.info("Payment", extra={"card_number": card_number})

# ✅ GOOD: Never log PII or payment details
logger.info("Payment processed", extra={"amount_cents": amount_cents})
```

## Success Criteria

- Every request has `X-Request-ID` in logs and response
- All mutations emit audit logs
- No PII or sensitive data in logs
- Worker errors logged at ERROR level
- Structured JSON format for production
- Worker heartbeat logs every N iterations
- WS messages carry request_id trace
- Crash loop detected and alerted