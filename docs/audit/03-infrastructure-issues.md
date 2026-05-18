# Infrastructure Issues Analysis

> **Date**: 2026-05-17
> **Scope**: `backend/infrastructure/`, `backend/app/db/`, `backend/app/core/`

---

## 1. Database Layer

### 1.1 No `pool_pre_ping` on Engine

**File**: `infrastructure/db/session.py:17-24`

The async engine has `pool_size=10`, `max_overflow=20`, `pool_timeout=30`, `pool_recycle=1800`, but **NO `pool_pre_ping=True`**.

**Risk**: Stale database connections are not detected before use. A connection that was idle for more than `pool_recycle` (1800s) or was terminated by the DB will cause an error at query time instead of being transparently replaced.

**Fix**: Add `pool_pre_ping=True` to `create_async_engine()`.

### 1.2 `create_all` in Lifespan Duplicates Migrations

**File**: `backend/main.py:94-96`

```python
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)  # PRODUCTION: remove
```

Comment says "remove in production and run alembic upgrade head in CI/CD" but there's no environment guard. In production, both `create_all` and Alembic would run, potentially causing:
- Silent schema changes without migration tracking
- Drift between local `create_all` and migration-based state
- Missing `alembic_version` table

**Fix**: Guard with `if settings.RAYCARWASH_ENV == "development"`.

### 1.3 `_get_encryption_key()` Late Failure

**File**: `infrastructure/db/base.py:14-16`

```python
def _get_encryption_key():
    return base64.b64decode(get_settings().ENCRYPTION_KEY)
```

Called lazily when an encrypted column is first accessed. If `ENCRYPTION_KEY` is invalid or missing, it crashes at runtime, not at import/startup.

**Fix**: Validate encryption key in lifespan startup.

---

## 2. Redis Layer

### 2.1 No Connection Pool Configuration

**File**: `infrastructure/redis/client.py:18`

```python
redis = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
```

No `pool_size`, `timeout`, `retry_on_timeout`, or `socket_keepalive` parameters. Uses Redis defaults.

**Risk**: In production under load:
- Default pool size may be too small (connection exhaustion)
- No timeout → calls may hang indefinitely if Redis is slow
- No retry → transient failures propagate immediately

**Fix**: Add explicit pool configuration matching DB settings.

### 2.2 fakeredis Fallback Masks Parity Issues

**File**: `infrastructure/redis/client.py:29-31`

```python
if not redis_available:
    import fakeredis
    redis = fakeredis.FakeRedis()
```

fakeredis doesn't support all Redis commands (Pub/Sub, some data structures). Dev and prod behavior differ significantly. Some features work in dev but fail in production.

**Fix**: Log a clear warning when falling back; consider failing hard in CI.

### 2.3 No Timeout Parameter

**File**: `infrastructure/redis/client.py:18`

`aioredis.from_url()` called without `socket_timeout` or `socket_connect_timeout`. If Redis becomes slow or unreachable after initial connect, operations may hang indefinitely.

---

## 3. Email Layer

### 3.1 No Retry Logic for SMTP Failures

**File**: `infrastructure/email/service.py:119-120`

```python
except smtplib.SMTPException as e:
    logger.error("SMTP send failed", error=str(e))
```

On transient SMTP failure, the error is logged but NOT retried. The email is silently lost.

### 3.2 Only Catches `SMTPException`

**File**: `infrastructure/email/service.py:119`

Only catches `smtplib.SMTPException`. A `ConnectionRefusedError`, `socket.gaierror` (DNS failure), or `TimeoutError` would propagate as an unhandled exception to the caller.

### 3.3 Synchronous SMTP in Request Cycle

Email is sent within the request-response cycle (wrapped in `asyncio.to_thread`). If SMTP is slow, the HTTP response may time out.

**Fix**: Consider a background email queue.

---

## 4. NHTSA / VIN Lookup

### 4.1 No Retry for Transient API Failures

**File**: `infrastructure/nhtsa/client.py:58-73`

5xx or network errors from NHTSA API immediately return 503 with no retry.

### 4.2 New HTTP Client Per Call

**File**: `infrastructure/nhtsa/client.py:58`

```python
async with httpx.AsyncClient(timeout=10.0) as client:
```

Creates a new connection pool on every VIN lookup. For high-traffic scenarios, this is inefficient.

### 4.3 Domain Import in Infrastructure

**File**: `infrastructure/nhtsa/client.py:14`

```python
from domains.vehicles.models import VehicleSize
```

Infrastructure should NOT import from domain code. `VehicleSize` should be in `shared/`.

---

## 5. H3 Spatial Indexing

### 5.1 `db.commit()` Inside Infrastructure Function

**File**: `infrastructure/h3/client.py:90`

```python
await db.commit()  # Called inside infrastructure layer
```

The calling service has no control over the transaction boundary. Violates repository pattern.

### 5.2 Inconsistent State Risk

**File**: `infrastructure/h3/client.py:72-90`

If Redis SADD succeeds but DB update fails, the Redis set contains a stale entry that expires naturally via TTL. Not catastrophic but inconsistent.

### 5.3 Silent Failure with fakeredis

When using fakeredis (dev mode), the H3 matching function silently returns empty results with no log warning.

---

## 6. Payments / Stripe

### 6.1 No Retry for Stripe API Failures

**File**: `infrastructure/payments/stripe_test.py:40-50`

No automatic retry on Stripe transient errors (rate limits, 5xx).

### 6.2 Empty `infrastructure/stripe/` Directory

**File**: `infrastructure/stripe/__init__.py`

Completely empty. Appears to be dead code — Stripe logic lives in `infrastructure/payments/`.

---

## 7. Webhook Security

### 7.1 Body Size Limit — Content-Length Bypass

**File**: `backend/main.py:262-275`

The body size limit middleware checks `Content-Length` header but a malicious client could send a small header value with a large body. The real guard is at the ASGI layer.

### 7.2 Placeholder Webhook Secret Skips Verification

**File**: `domains/payments/webhook_router.py:78-95`

If `STRIPE_WEBHOOK_SECRET` is a placeholder (starts with `sk_test_`), signature verification is skipped entirely with just a log warning. This is acceptable for dev but easy to miss in production configuration.

---

## 8. Missing Production Adapters

| Adapter | Status | Production Impact |
|---------|--------|-------------------|
| S3 Storage | Throws `RuntimeError` | File uploads crash |
| Twilio SMS | Throws `NotImplementedError` | SMS OTP fails |
| Google Maps Geocoding | Throws `RuntimeError` | Falls back to Nominatim (1 req/s) |

---

## 9. Seed Data Issues

### 9.1 `pool_pre_ping` Missing (Duplicate)

Already covered in 1.1.

### 9.2 Seed Functions Run Every Startup

**File**: `app/db/seed.py`, `seed_rbac.py`, `detailer_seed.py`

All seed functions are idempotent via `select().where()` checks, but they run on every startup. For production, this is unnecessary I/O. Should be gated behind an env flag.

---

## 10. Miscellaneous

### 10.1 Config Validator Uses `warnings.warn` Instead of Raising

**File**: `backend/app/core/config.py`

```python
warnings.warn("Using placeholder Stripe key")  # Not visible in production logs
```

Should use `logger.warning()` for production visibility.

### 10.2 `float("inf")` in Pydantic Settings

**File**: `backend/app/core/config.py`

`SURGE_THRESHOLDS` uses `float("inf")` which may not serialize properly via Pydantic.

---

## Summary — Infrastructure Priority Matrix

| Priority | Fix | File |
|----------|-----|------|
| P0 | Add `pool_pre_ping` to DB engine | `infrastructure/db/session.py` |
| P0 | Guard `create_all` with env check | `backend/main.py:94-96` |
| P0 | Fix domain import in NHTSA | `infrastructure/nhtsa/client.py:14` |
| P1 | Add Redis pool config | `infrastructure/redis/client.py:18` |
| P1 | Add SMTP retry + broader exception handling | `infrastructure/email/service.py` |
| P1 | Move `db.commit()` out of H3 infra | `infrastructure/h3/client.py:90` |
| P1 | Validate encryption key at startup | `backend/main.py` |
| P2 | Fix `warnings.warn` → `logger.warning` | `backend/app/core/config.py` |
| P2 | Gate seed functions behind env flag | `app/db/*.py` |
| P3 | Add NHTSA retry logic | `infrastructure/nhtsa/client.py` |
| P3 | Remove empty `infrastructure/stripe/` | `infrastructure/stripe/` |
