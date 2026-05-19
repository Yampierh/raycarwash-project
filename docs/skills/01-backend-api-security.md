# Skill 01: Backend API Security

> **Discipline:** Security
> **Applies to:** All new API endpoints — especially public-facing and financial mutations
> **Source audit:** `docs/plans/22-security-architecture-audit.md` (findings H1, H2, H4, H6, H7)

---

## Overview

Every new endpoint must pass this security checklist before being considered "production-ready." This skill codifies the security posture of the RayCarWash API: rate limiting, idempotency, input validation, data exposure prevention, and CORS hardening.

---

## Prerequisites

- Read `AGENTS.md` — understand the auth flow (access/refresh/onboarding tokens)
- Read `.claude/execution_protocol.md` — mandatory pipeline for backend changes
- Read `docs/plans/22-security-architecture-audit.md` — understand past findings
- Read relevant contract plan (19/20/21) for rate limit and validation specifics

---

## Checklist (per endpoint)

### 1. Authentication & Authorization

- [ ] Public endpoint? Skip auth, apply aggressive rate limits
- [ ] Authenticated endpoint? Verify JWT role matches required role (`client`, `detailer`, `admin`)
- [ ] Resource ownership check? User can only access their own data (IDOR prevention)
  ```python
  # GOOD — checks ownership
  if appointment.user_id != current_user.id:
      raise HTTPException(403, "Not your appointment")
  ```
- [ ] Step-up auth needed? (e.g., Stripe Connect requires `step-up` scope)

### 2. Rate Limiting

- [ ] Rate limit defined in contract (req/min per IP or per user)
- [ ] Public POST endpoints: **aggressive** limits (3-10/min)
- [ ] Public GET endpoints: moderate limits (30-60/min)
- [ ] Authenticated mutations: per-user limits (10-20/min)
- [ ] Financial endpoints: **most aggressive** (3/min — cash-out, cancel)
- [ ] Error response includes `Retry-After` header
- [ ] Rate limit applied via `slowapi` decorator or router config

### 3. Idempotency

- [ ] Every mutation endpoint requires `Idempotency-Key` header
- [ ] **CRITICAL: Cache key includes authenticated user ID**
  ```python
  # WRONG — cross-user collision
  key = f"idempotency:anon:{method}:{path}:{idempotency_key}"
  # RIGHT — user-scoped
  key = f"idempotency:{user_id}:{method}:{path}:{idempotency_key}"
  ```
- [ ] Financial mutations (cash-out, cancel-refund): idempotency required + app-level guard (check status in transaction)
- [ ] Response includes `Idempotency-Key` in response headers for idempotent endpoints

### 4. Input Validation

- [ ] Every string field: `Field(..., max_length=N, strip_whitespace=True)`
- [ ] Email fields: email-validator + lowercase + strip
- [ ] Enum fields: use Python `Enum` type, not free strings
  ```python
  # WRONG — vulnerable to injection
  filter = request.query_params["filter"]
  # RIGHT — mapped through enum
  filter = CustomerFilter(request.query_params["filter"])
  ```
- [ ] XSS sanitization on all user-generated text (message, reply, review body)
- [ ] UUID path params: validate UUID format before DB query
- [ ] Monetary values: validate positive integer, max reasonable value

### 5. Data Exposure

- [ ] Responses only include fields the consumer needs (principle of least data)
- [ ] PII encrypted at rest (use `EncryptedType` from infrastructure)
- [ ] Business metrics exposed publicly? Round/approximate values, cache aggressively
- [ ] No internal IDs exposed unless necessary (use UUIDs, not auto-increment)
- [ ] Phone numbers masked? (e.g., `(260) 555-****` for non-essential views)

### 6. Response Headers

- [ ] `Cache-Control: no-store` on all auth-required endpoints
- [ ] `Cache-Control: public, max-age=N` on cacheable public endpoints
- [ ] `X-Request-ID` present (via middleware)
- [ ] `X-Process-Time` present (via middleware)
- [ ] `X-Cache: HIT|MISS|DYNAMIC` on cacheable endpoints

### 7. Error Responses

- [ ] Error responses use `ErrorEnvelope` schema (consistent format)
- [ ] 400 for validation errors with field-level details
- [ ] 409 for business rule conflicts (duplicate, already canceled, etc.)
- [ ] 429 for rate limiting with `Retry-After`
- [ ] Never expose stack traces or internal error details in production responses

---

## Common Pitfalls

| Pitfall | Consequence | Reference |
|---------|-------------|-----------|
| Idempotency key without user_id | Cross-user cache poisoning | Audit H1 |
| Missing rate limits on public POST | Email bombing, spam | Audit H2 |
| String interpolation in filter params | SQL injection | Audit H7 |
| Exposing raw business metrics | Competitive intelligence | Audit H6 |
| Missing 409 on business rule violations | Confusing client behavior | Audit H9 |
| PII in audit log plaintext | Compliance violation | AGENTS.md |

---

## Examples from RayCarWash

### Public endpoint (contract 19 — testimonials)
```python
@router.get("/public/testimonials")
@limiter.limit("60/minute")
async def get_testimonials(
    role: Optional[Literal["client", "detailer"]] = None,
    limit: int = Query(default=10, le=50),
    featured: bool = False,
    cache: CacheService = Depends(get_cache),
):
    cached = await cache.get("public:testimonials")
    if cached:
        return Envelope(data=cached, headers={"X-Cache": "HIT"})
    # ... query ...
    await cache.set("public:testimonials", response, ttl=3600)
    return Envelope(data=response, headers={"X-Cache": "MISS"})
```

### Financial mutation (contract 20 — cash-out)
```python
@router.post("/detailers/me/earnings/cash-out")
@limiter.limit("3/minute")
async def cash_out(
    body: CashOutRequest,
    current_user: User = Depends(require_role("detailer")),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # 1. Idempotency check (middleware handles this)
    # 2. Validate amount_cents > 0 and <= pending
    # 3. BEGIN transaction
    # 4. SELECT ... FOR UPDATE on pending cash-outs
    # 5. If exists → 409 Conflict
    # 6. Create cash-out record
    # 7. Stripe transfer
    # 8. Audit log
    # 9. COMMIT
```
