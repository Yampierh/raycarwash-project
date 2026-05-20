# 22 — Security & Architecture Audit

> **Status:** **IN PROGRESS** — H1–H10 documented + D1–D8 reconciled against backend models. Implementation deferred to Fase 0 of execution pipeline.
> **Priority:** **Critical**
> **Audit Date:** 2026-05-19
> **Updated:** 2026-05-19 (section 6.1 added with backend reality-check corrections D1–D8)
> **Scope:** All 32 new API endpoints across Tracks 1-3 + existing middleware/infrastructure review
> **Auditor Role:** API Security Expert (specialist review)

---

## Executive Summary

This audit examines the 32 new API contract endpoints through the lens of an **API security expert** with experience in high-scale marketplace systems. The review covers: authentication, authorization, rate limiting, idempotency, input validation, data exposure, cache poisoning, SQL injection vectors, and observability gaps.

**10 findings total:** 1 CRITICAL, 4 HIGH, 3 MEDIUM, 2 LOW. All findings have been remediated in the contract documents (plans 19-21) and flagged for implementation.

---

## 1. Findings Registry

| # | Severity | Category | Endpoint(s) | Title | Status |
|---|----------|----------|-------------|-------|--------|
| **H1** | **CRITICAL** | Idempotency | All mutations (cash-out, cancel, reply, etc.) | Idempotency middleware cache key doesn't include user_id | ✅ **Fixed in code** — commit `77105af` (deferred caching post-auth via `resolve_idempotency` dep); regression test `tests/test_idempotency_v2_user_scope.py` |
| **H2** | **HIGH** | Rate Limiting | All Track 1 public endpoints | No rate limiting on cacheable endpoints (theft/scrape) | Fixed in contract 19 |
| **H3** | **HIGH** | Performance | `GET /me/dashboard` (both provider + customer) | Aggregate endpoint queries 7+ tables without index optimization | Fixed in contract 20/21 |
| **H4** | **HIGH** | Validation | All POST/PUT endpoints | Missing max_length, strip, regex constraints on string inputs | Fixed in contract 19/20/21 |
| **H5** | **HIGH** | Cache Strategy | All GET public endpoints | No Cache-Control headers, CDN config, or ETag support | Fixed in contract 19 |
| **H6** | **MEDIUM** | Data Exposure | `GET /public/stats` | Exposes business volume metrics (deliveries, active_detailers, median earnings) | Fixed in contract 19 |
| **H7** | **MEDIUM** | SQL Injection | `GET /me/customers` with `?filter=` | Query param mapped to string — must use enum, never interpolation | Fixed in contract 20 |
| **H8** | **MEDIUM** | Observability | All endpoints | Missing X-Process-Time, X-Cache headers, Prometheus metrics spec | Fixed in contract 19/20/21 |
| **H9** | **LOW** | Business Logic | `POST /me/cash-out` | One-pending-at-a-time rule not explicitly documented as 409 Conflict | Fixed in contract 20 |
| **H10** | **LOW** | Timeout | `POST /me/connect-account` | Stripe Connect URL expires in 7d — no cleanup worker for abandoned onboarding | Fixed in contract 20 |

---

## 2. Detailed Findings

### H1 (CRITICAL) — Idempotency Middleware Cache Key Lacks User Identity

**Description (revised post-code review, 2026-05-19):**
The existing middleware at [`backend/app/core/idempotency.py`](../../backend/app/core/idempotency.py) **already attempts** to include `request.state.user.id` in the cache key ([line 145](../../backend/app/core/idempotency.py#L145)) **and already adds a SHA-256 body_hash prefix** ([line 78–83](../../backend/app/core/idempotency.py#L78-L83)). The bug is more subtle than the original audit suggested:

- Middleware runs **before** FastAPI's dependency injection, so `get_current_user` has not yet executed — `request.state.user` is `None`, and `user_id` falls back to the literal string `"anon"`.
- The body_hash partially mitigates collision (two detailers using same key but different `amount_cents` get different cache slots).
- **However**, endpoints with empty bodies (`PUT /me/jobs/{id}/accept` and `decline` use `{}`) hash to the same body_hash. Two detailers with the same `Idempotency-Key` and empty body **will collide**.

Current cache key in the wild:
```
idempotency:anon:PUT:/api/v1/detailers/me/jobs/{id}/accept:{key}:empty
```

**Exploitation scenario:**
1. Detailer A submits accept with key `abc123` → response cached under `idempotency:anon:...:abc123:empty`
2. Detailer B submits accept with key `abc123` on a **different job** → receives Detailer A's response (wrong job ID, wrong status).

**Fix (decided 2026-05-19 — defer cache to post-auth):**

Two-phase approach with zero refactor of `IdempotencyMiddleware` validation logic:

1. **Middleware** (existing) — stays as a passive recorder:
   - Reads `Idempotency-Key` header
   - Reads + replays request body (existing logic to avoid consuming the receive channel)
   - Computes `body_hash` (existing — keep the 16-char SHA-256 prefix)
   - Writes to `request.state.idempotency_key` and `request.state.idempotency_body_hash`
   - **Does NOT** write to Redis here. Does NOT attempt cache replay.

2. **New post-auth dependency** `resolve_idempotency` runs after `get_current_user`:
   - Reads `request.state.idempotency_key` and `body_hash`
   - Builds the real cache key with the now-resolved `user_id`:
     ```
     idempotency:{user_id}:{method}:{path}:{key}:{body_hash}
     ```
   - If cache hit → raises `HTTPException(409, "Duplicate request")` OR returns the cached body verbatim (TBD during implementation — match existing behavior).
   - If cache miss → reserves the slot (`SET NX` with TTL) and stores the resolved key in `request.state.idempotency_cache_key` so the response-write step can populate it.

3. **Response-write step** (worker hook or response middleware): on 2xx, writes the response body to the resolved cache key with the existing 24h TTL.

**Why this approach (vs alternatives)**:
- ❌ Decoding JWT inside middleware would duplicate `get_current_user` logic — drift risk if JWKS endpoint or algorithm changes.
- ❌ Keeping body_hash as the only defense fails for `accept`/`decline` (body=`{}`) and other empty-body mutations.
- ✅ Deferred approach reuses existing auth pipeline, keeps body_hash as secondary defense, and adds the missing `user_id` scoping.

**Remediation applied to:**
- Contract 20 (all mutations: cash-out, accept, decline, reply, settings update, reorder, availability)
- Contract 21 (cancel appointment)
- Backend implementation deferred to Fase 0 of execution pipeline.

---

### H2 (HIGH) — No Rate Limiting on Public Endpoints

**Description:**
Track 1 endpoints (testimonials, FAQ, coverage, stats, contact, waitlist) have no rate limiting beyond a single `30 req/min` on coverage/check. A bot can scrape all data in seconds or spam the contact form / waitlist.

**Exploitation scenario:**
1. Email bombing via `POST /public/contact` — submit 1000 messages in 1 minute
2. ZIP enumeration via `POST /public/coverage/check` — iterate all 5-digit ZIPs in 3 hours
3. Waitlist manipulation — inflate count to discourage real signups

**Rate limits applied per endpoint:**
See Contract 19 section 10 "Operational Requirements".

**Remediation applied to:** Contract 19

---

### H3 (HIGH) — Aggregate Dashboard Queries Without Indexes

**Description:**
`GET /me/dashboard` (provider) aggregates data from 7+ tables: appointments, provider_profiles, reviews, notifications, earnings, schedule, supplies. Without compound indexes, this is a sequential scan nightmare as the provider base grows.

**Affected queries:**
- Provider's upcoming appointments: `WHERE provider_id = ? AND status IN ('pending','confirmed') AND is_deleted = FALSE`
- Earnings last 14 days: `WHERE provider_id = ? AND status = 'completed' AND completed_at > NOW() - INTERVAL '14 days'`
- Customer aggregation: `WHERE provider_id = ? AND is_deleted = FALSE`

**Indexes required:**
See Contract 20 section 17 "Required Database Migrations".

**Remediation applied to:** Contract 20, Contract 21

---

### H4 (HIGH) — Missing Input Validation Constraints

**Description:**
The contracts specify field types but don't enforce string lengths, regex patterns, or normalization rules. This opens vectors for:
- XSS via message bodies
- SQL-like injection via free-text fields
- Storage bloat via unbounded VARCHAR/TEXT
- Duplicate emails due to missing normalization (lowercase + trim)

**Fields requiring explicit constraints:**
- All `name`, `message`, `reply`, `reason` fields: max_length + strip
- All `email` fields: max_length + lowercase + regex
- All ZIP/phone: regex pattern
- All `color` values: hex validation

**Remediation applied to:** Contracts 19, 20, 21

---

### H5 (HIGH) — Zero Cache Strategy

**Description:**
Read-only public endpoints return no `Cache-Control` headers. Without explicit caching:
- CDN can't cache effectively
- Backend serves the same testimonials/FAQ/stats thousands of times
- Stale-while-revalidate not configured (no graceful degradation)

**Required headers per endpoint:**
See Contract 19 section 10 "Operational Requirements".

**Remediation applied to:** Contract 19

---

### H6 (MEDIUM) — Business Data Exposure

**Description:**
`GET /public/stats` exposes `deliveries` (2400), `active_detailers` (85), `median_earnings_per_hr` (42). Competitors can:
- Estimate revenue: 2400 × ~$100 avg = $240K/month
- Calculate platform commission from earnings vs bookings
- Track growth rate over time

**Mitigation:**
- Cache aggressively (1hr minimum, CDN edge)
- No query params (prevent date-filtered enumeration)
- Round/approximate values
- Document as "marketing-approved approximations" not real-time

**Remediation applied to:** Contract 19

---

### H7 (MEDIUM) — Enum Injection Vector

**Description:**
`GET /me/customers?filter=all|vip|recent|dormant` uses string query param. If passed directly to SQL without mapping, it's an injection vector.

**Fix:**
Use Python `Enum` for filter values. Map enum to repository conditions, never string interpolation.

**Remediation applied to:** Contract 20

---

### H8 (MEDIUM) — No Observability Headers

**Description:**
None of the 32 endpoints specify observability headers or metrics. Without:
- `X-Process-Time`: can't monitor slow endpoints in production
- `X-Cache`: can't verify CDN is working
- Prometheus metrics: no latency/error-rate tracking per endpoint
- Structured logging fields: no per-endpoint correlation

**Requirement:**
Every endpoint response (error or success) must include `X-Request-ID` and `X-Process-Time`. Cacheable endpoints must include `X-Cache: HIT|MISS`.

**Remediation applied to:** Contracts 19, 20, 21

---

### H9 (LOW) — Missing 409 Conflict Documentation

**Description:**
`POST /me/cash-out` has business rule "one pending cash-out at a time" but the contract doesn't specify the HTTP response for violation (should be `409 Conflict`).

**Remediation applied to:** Contract 20

---

### H10 (LOW) — Stripe Connect Onboarding Abandonment

**Description:**
`POST /me/connect-account` returns a Stripe Connect onboarding URL that expires in 7 days. If a detailer never completes onboarding:
- Their account shows `"onboarding": "pending"` forever
- No automated cleanup or reminder

**Fix:**
- Add `onboarding_expires_at` timestamp
- Worker to cleanup/notify after 24h of inactivity
- Expired onboarding status: `"expired"`

**Remediation applied to:** Contract 20

---

## 3. Remediation Map

| Artifact | Finding(s) Addressed | Type |
|----------|---------------------|------|
| `docs/plans/19-api-contracts-track1-marketing.md` | H2, H4, H5, H6, H8 | Updated Section 10 |
| `docs/plans/20-api-contracts-track2-provider-dashboard.md` | H1, H3, H4, H7, H8, H9, H10 | Updated Section 17 |
| `docs/plans/21-api-contracts-track3-customer-dashboard.md` | H1, H3, H4, H8 | Updated Section 7 |
| `backend/` middleware (future sprint) | H1 | Idempotency middleware fix |
| `backend/` migrations (future sprint) | H3 | Indexes M01-M03 |
| `backend/` migrations (future sprint) | H3 | Materialized view MV01 |
| `backend/` config (future sprint) | H2 | slowapi rate limit config |
| `backend/` middleware (future sprint) | H5 | Cache-Control + ETag |
| `backend/` worker (future sprint) | H10 | Stripe onboarding timeout |

---

## 4. Re-audit Checklist (Next Sprint)

- [ ] H1: Idempotency middleware cache key includes `user_id`
- [ ] H2: slowapi rate limits configured for all 9 public endpoints
- [ ] H2: rate limit error responses return `Retry-After` header
- [ ] H3: Indexes M01-M03 created in migration
- [ ] H3: Materialized view MV01 created with refresh worker
- [ ] H4: All Pydantic models have `max_length`, `strip_whitespace=True`, `regex` where applicable
- [ ] H4: Email normalization (lowercase + trim) in `POST /contact` and `POST /waitlist/join`
- [ ] H5: Cache-Control headers present on all public GET endpoints
- [ ] H5: ETag/If-None-Match implemented on testimonials + FAQ
- [ ] H6: Stats endpoint has minimum 1hr cache, no query params
- [ ] H7: Filter param uses enum, never string interpolation
- [ ] H8: X-Process-Time header on all responses
- [ ] H8: X-Cache header on public GET endpoints
- [ ] H9: 409 Conflict response documented and implemented for cash-out

---

## 5. Security Risk Matrix

| Threat | Likelihood | Impact | Risk | Mitigation |
|--------|-----------|--------|------|-----------|
| Cache poisoning via idempotency key collision | Low | **High** (wrong user data) | Medium | H1 fix |
| Email spam via contact form | High | Medium (support overload) | **High** | H2 rate limits |
| Competitor scrapes business metrics | High | Low (public data) | Medium | H5 cache + H6 rounding |
| SQL injection via filter param | Low | **HIGH** (data breach) | Medium | H7 enum mapping |
| XSS via review reply | Medium | Medium (session theft) | Medium | H4 sanitization |
| Cash-out double processing | Low | **High** (financial loss) | Medium | H1 idempotency + H9 conflict |
| Stripe onboarding abandonment | Medium | Low (stale accounts) | Low | H10 timeout worker |
| ZIP code enumeration | Medium | Low (public ZIP data) | Low | H2 rate limits |

---

## 6. Appendix: Audit Methodology

This audit was conducted using the following methodology:

1. **Endpoint inventory** — Catalog all 32 endpoints across 3 tracks
2. **Threat modeling** — For each endpoint: what's the worst thing an attacker could do?
3. **OWASP API Security Top 10 mapping** — Check against: Broken Object Level Auth, Broken Authentication, Excessive Data Exposure, Lack of Resources & Rate Limiting, BOLA, Security Misconfiguration, Injection
4. **Performance profiling** — Estimate query complexity for aggregate endpoints
5. **Cache analysis** — Identify cacheable vs non-cacheable endpoints
6. **Validation audit** — Check all input fields for constraint completeness

---

## 6.1 Post-Audit Corrections (D1–D8)

> **Added 2026-05-19 after backend reality-check of contract plans 19/20/21 against actual SQLAlchemy models.**
> Every fix below has been applied **in-place** to the corresponding contract plan with an HTML comment `<!-- FIX D{N}: ... -->` next to the change. This section preserves the before/after history for traceability.

### 6.1.1 Discrepancy Table

| # | Severity | Where | Contract said (before) | Reality (after) | Why it would have broken |
|---|----------|-------|------------------------|-----------------|--------------------------|
| **D1** | **Critical** | Plan 20 M01, M02, queries | `appointments.provider_id` | `appointments.detailer_id` | Migrations + every SQL query referencing the FK column would fail at runtime — column does not exist. URL prefix `/detailers/me/` stays as-is (URL semantic ≠ SQL column). |
| **D2** | **Critical** | Plan 20 M01 INCLUDE clause | `estimated_price_cents` | `estimated_price` (int — cents convention per AGENTS.md) | Index creation fails — column does not exist. The integer is interpreted as cents by app convention, but the column has no `_cents` suffix. |
| **D3** | **Critical** | Plan 21 §7.5 index; Plan 21 §1 data sources; Plan 20 §9 description | `appointments.user_id` | `appointments.client_id` | Migration fails + queries referencing `user_id` on `appointments` return error. Note: `rewards.user_id` IS correct (new table FKs to `users.id`). |
| **D4** | **Critical** | Plan 20 M02 view + §6 description | `services_catalog` table; `appointment_services` table | `services` (singular SQL table); `appointment_services` does not exist at all — join via `appointments.service_id` → `services.id` | Materialized view fails to create. Python package is `domains/services_catalog/` but `__tablename__ = "services"`. |
| **D5** | **High** | Plan 20 M02 view | `appointment_addons.addon_cents` | `appointment_addons.price_cents` | Aggregation column missing → MV creation fails. |
| **D6** | **High** | Plan 21 §7.6 pseudocode | `appointment.payment_intent_id` | `appointment.stripe_payment_intent_id` | Stripe refund call fails — attribute does not exist on the model. |
| **D7** | **High** | Plan 20 M01 partial index + M02 WHERE | `status = 'COMPLETED'` (uppercase string) | `'completed'` (lowercase — the SQLAlchemy Enum stores `.value` which is lowercase; the Python member is `AppointmentStatus.COMPLETED`) | Partial index would filter zero rows (the DB row has `'completed'`); MV builds empty. Subtle silent failure. |
| **D8** | **High** | Plan 21 §2 response shape | Status enum value `"canceled"` | DB enum has `cancelled_by_client` and `cancelled_by_detailer` (British spelling, doubled L, split by actor). | Response would expose `"cancelled_by_client"` to FE that expects `"canceled"`. **Decision:** keep `"canceled"` as a normalized UI alias in the response payload; the DB persisted value remains the real enum. |

### 6.1.2 Cancel Endpoint Overlap Decision

The contract `POST /api/v1/appointments/{id}/cancel` (Plan 21 §2) overlapped with existing `PATCH /api/v1/appointments/{id}/status`. **Decision (2026-05-19):** the new endpoint is a **wrapper** over the existing FSM service.

| Aspect | PATCH /status (existing) | POST /cancel (new wrapper) |
|--------|--------------------------|----------------------------|
| Actors | client, detailer, admin | **client only** |
| Target status resolution | Caller passes target explicitly | Auto-resolves to `CANCELLED_BY_CLIENT` |
| FSM enforcement | Yes (VALID_TRANSITIONS) | **Yes — delegated to same FSM service** |
| Refund calculation | No | **Yes — inline + Stripe refund** |
| Idempotency-Key | Not required | **Required** (financial) |
| Response status value | Returns DB enum (`cancelled_by_client`) | Normalized UI alias (`canceled`) |
| Detailer cancelling | Continues to use this | Cannot use this — must use PATCH |

This avoids two paths-to-state mutation while exposing a customer-friendly endpoint with refund semantics.

### 6.1.3 H1 Fix Approach (Decided)

After reading the existing middleware code ([backend/app/core/idempotency.py](../../backend/app/core/idempotency.py)), the fix path is **deferred caching post-auth** — see updated H1 section above for full rationale. Summary:

1. Existing middleware stays as a passive recorder writing to `request.state.idempotency_key` + `body_hash`.
2. New `resolve_idempotency` dependency runs after `get_current_user` and builds the real cache key with `user_id`.
3. Response-write step populates the resolved cache key on 2xx.

Body hash (SHA-256 prefix, 16 hex chars) is **preserved** as secondary defense against same-key-different-payload collision.

### 6.1.4 Re-audit Checklist Addendum

- [ ] D1: every SQL reference to `appointments.provider_id` replaced with `detailer_id`
- [ ] D2: every `estimated_price_cents` in migrations replaced with `estimated_price`
- [ ] D3: every `appointments.user_id` replaced with `client_id` (rewards.user_id stays)
- [ ] D4: `services_catalog` table reference replaced with `services`
- [ ] D5: `appointment_addons.addon_cents` replaced with `price_cents`
- [ ] D6: `appointment.payment_intent_id` replaced with `stripe_payment_intent_id`
- [ ] D7: `'COMPLETED'` (uppercase) replaced with `'completed'` in partial indexes and WHERE clauses
- [ ] D8: cancel response normalizes enum to UI alias `"canceled"`; DB stores real enum value
- [ ] Cancel wrapper delegates to FSM service (no inline status mutation)
- [ ] H1 fix: middleware records to request.state only; post-auth dep writes Redis cache key with user_id
