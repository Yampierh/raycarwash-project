# Skill 03: Backend Observability

> **Discipline:** Monitoring, Logging & Tracing
> **Applies to:** Every new endpoint, worker, and background task
> **Source audit:** `docs/plans/22-security-architecture-audit.md` (finding H8)

---

## Overview

RayCarWash uses structured JSON logging with `X-Request-ID` propagation, Prometheus metrics, and append-only audit logs. Every new endpoint must emit logs, metrics, and audit records at the appropriate levels.

---

## Prerequisites

- Read `AGENTS.md` — middleware stack order (RequestID → StructuredLogging → AuditContext → Idempotency)
- Read `.claude/execution_protocol.md` — OBSERVABILITY is step 5 of 6

---

## Checklist

### 1. Structured Logging

- [ ] Every request logs: `method`, `path`, `status_code`, `process_time_ms`, `user_id` (if auth'd)
- [ ] Every error logs: `error_type`, `error_message`, `traceback` (DEBUG only)
- [ ] PII is never logged (email, phone, address are redacted automatically by middleware)
- [ ] Log level discipline:
  | Level | When |
  |-------|------|
  | `ERROR` | Unhandled exceptions, 5xx responses |
  | `WARNING` | Rate limit exceeded, 4xx business errors |
  | `INFO` | Request start/end, successful mutations |
  | `DEBUG` | SQL queries, cache operations (local dev only) |

### 2. Prometheus Metrics

Every endpoint group must register these metrics:

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["endpoint", "method", "status"],
)

http_request_duration_ms = Histogram(
    "http_request_duration_ms",
    "Request duration in ms",
    ["endpoint", "method"],
    buckets=[5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)
```

- [ ] `http_requests_total` — label by endpoint, method, status
- [ ] `http_request_duration_ms` — label by endpoint, method
- [ ] `rate_limit_exceeded_total` — label by endpoint (for rate limiting alerts)
- [ ] Business metrics as appropriate (cash-out attempts, refund totals, etc.)

### 3. HTTP Response Headers

| Header | All Endpoints | Public GET Only |
|--------|:---:|:---:|
| `X-Request-ID` | ✓ | ✓ |
| `X-Process-Time` | ✓ | ✓ |
| `X-Cache` | — | ✓ (HIT/MISS/DYNAMIC) |
| `Retry-After` | Only on 429 | Only on 429 |

### 4. Audit Logging

Every mutation must write to the audit log (append-only, JSONB):

```python
await audit_log.write(
    action="cash_out.requested",
    entity_type="cash_out",
    entity_id=str(cash_out.id),
    user_id=current_user.id,
    provider_id=current_user.provider_id,
    metadata={
        "amount_cents": body.amount_cents,
        "pending_cents_before": pending_cents,
    },
    ip_address=request.client.host,
    idempotency_key=idempotency_key,
)
```

- [ ] All mutations logged (create, update, delete, status transitions)
- [ ] Read operations NOT logged (too noisy)
- [ ] Metadata includes before/after values for financial mutations
- [ ] IP address + idempotency key always included for traceability

### 5. Health Checks

- [ ] `GET /health` — returns `{"status": "ok"}` (exist)
- [ ] `GET /health/ready` — checks DB + Redis connectivity
- [ ] `GET /health/db` — lightweight `SELECT 1`
- [ ] No auth required on health check endpoints

### 6. Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| p95 latency per endpoint | >500ms | >2s |
| Error rate (5xx) | >1% | >5% |
| Rate limit triggers per min | >100 | >500 |
| Cash-out failure rate | >5% | >10% |
| Audit log write failures | >0 in 5 min | >5 in 5 min |

---

## Common Pitfalls

| Pitfall | Impact | Solution |
|---------|--------|----------|
| Logging PII in mutation metadata | Compliance violation | Use Pydantic redact or middleware auto-redact |
| No `X-Process-Time` header | Can't monitor slow endpoints in production | Add to response middleware |
| Not labeling metrics by endpoint | Can't identify which endpoint is slow | Always include `endpoint` label |
| Audit log without idempotency key | Can't deduplicate during replay | Always include `idempotency_key` in audit metadata |
| Not distinguishing 4xx from 5xx in metrics | Can't detect real errors | Label by status code range |

---

## Examples from RayCarWash

### Middleware instrumentation pattern
```python
# Structured logging middleware (existing)
@router.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.state.request_id
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time, 2),
            "user_id": getattr(request.state, "user_id", None),
        },
    )
    response.headers["X-Process-Time"] = str(round(process_time, 2))
    return response
```

### Audit log for appointment cancel
```python
async def cancel_appointment(...):
    # ... in transaction ...
    await audit_log.write(
        action="appointment.canceled",
        entity_type="appointment",
        entity_id=str(appointment.id),
        user_id=current_user.id,
        metadata={
            "previous_status": appointment.status,
            "new_status": "canceled",
            "refund_cents": refund.cents,
            "refund_pct": refund.pct,
            "reason": reason,
            "scheduled_at": appointment.scheduled_time.isoformat(),
        },
        ip_address=request.client.host,
        idempotency_key=idempotency_key,
    )
```
