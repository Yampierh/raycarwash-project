# 20 — API Contracts: Track 2 — Provider Dashboard Endpoints

> **Status:** Contract — approved for implementation
> **Priority:** High
> **Design source:** `raycarwash/project/Provider Dashboard.html` + `dash-data.jsx` (full mock data schema, 197 lines, 12 data types)
> **Domain:** `backend/domains/providers/` (extend existing) + `backend/domains/admin/` (Stripe Connect)

---

## Overview

17 new endpoints powering 12 dashboard views for detailers. All require JWT with `role=detailer`.

All monetary values in **cents** (backend convention). Frontend divides by 100.

---

## Schemas Compartidos

```typescript
interface KpiDatum {
  value: number;         // primary value (cents or count)
  delta?: number;        // absolute change
  delta_pct?: number;    // percentage change
  unit?: string;         // e.g. "min", "sec"
}
```

---

## 1. `GET /api/v1/detailers/me/dashboard`

Aggregate endpoint — replaces multiple round-trips for Overview view.

```
Auth: JWT (role: detailer)
```

### Response

```typescript
// Envelope<DashboardResponse>
{
  "me": {
    "name": "Marcus Tate",
    "initials": "MT",
    "role": "Detailer · L3 Pro",
    "tier": "Gold",
    "rating": 4.92,
    "total_jobs": 312,
    "on_time_pct": 98,
    "member_since": "Jan 2024"
  },
  "kpis": {
    "today_jobs":       { "value": 5, "delta": 2, "delta_pct": 25 },
    "today_earnings":   { "value": 41200, "delta": 7800, "delta_pct": 18 },
    "week_earnings":    { "value": 214800, "delta": 31200, "delta_pct": 15 },
    "month_earnings":   { "value": 864200, "delta": -42800, "delta_pct": -4.7 },
    "rating":           { "value": 492, "delta": 4 },
    "completion_pct":   { "value": 98, "delta": 1 },
    "avg_ticket_cents": { "value": 15300, "delta": 700 },
    "response_sec":     { "value": 84, "delta": -18, "unit": "sec" }
  },
  "earnings_14d": [
    { "date": "2026-05-05", "base_cents": 12400, "tips_cents": 1800 }
  ],
  "incoming_jobs": [
    {
      "id": "uuid",
      "service_name": "Full detail · interior + ext",
      "addons": ["Pet hair", "Clay bar"],
      "vehicle": "2022 Honda Pilot",
      "location": "Aboite Twp · 4.2 mi",
      "scheduled_at": "2026-05-19T14:00:00Z",
      "pay_cents": 17900,
      "duration_min": 150,
      "customer_name": "Sarah K.",
      "customer_rating": 5.0,
      "is_new": true,
      "is_surge": false
    }
  ],
  "route": [
    {
      "stop_order": 1,
      "time": "08:30",
      "customer_name": "Jennifer R.",
      "service_name": "Full detail · Q5",
      "location": "Lakeside",
      "pay_cents": 17900,
      "status": "done"
    }
  ],
  "notifications": [
    {
      "id": "uuid",
      "title": "New job request",
      "body": "Sarah K. · Full detail · $179 · Today 2:00 PM",
      "time_ago": "2 min ago",
      "kind": "brand",
      "unread": true
    }
  ],
  "insights": [
    {
      "title": "You earn 24% more on Saturdays",
      "body": "Consider opening 2 more slots Sat morning",
      "icon": "trending"
    }
  ]
}
```

### Implementation notes

- `kpis.rating.value` is rating × 100 (e.g. 4.92 → 492)
- `earnings_14d` queries last 14 days from `provider_earnings` (new table) or aggregates from `appointments`
- `incoming_jobs` = appointments with status `pending` or `confirmed`
- `route` = today's appointments ordered by time
- `notifications` = recent unread from provider_notifications
- `insights` = computed from data patterns (can be static initially)

<!-- FIX D1: en SQL real, la columna de fk al detailer es `appointments.detailer_id` (no `provider_id`). Los endpoint paths `/detailers/me/...` usan el rol como prefijo URL pero las queries SQL apuntan a `detailer_id`. -->
<!-- FIX D2: la columna monetaria es `appointments.estimated_price` (int cents) y `actual_price` (int cents). Sin sufijo `_cents` por compatibilidad con código existente. Convención de cents está en AGENTS.md. -->
<!-- FIX D4: la tabla SQL es `services` (singular); el package Python es `domains/services_catalog/` pero el `__tablename__` es `services`. -->
<!-- FIX D5: addons usan `appointment_addons.price_cents` (no `addon_cents`). -->
<!-- FIX D7: los enum values en DB son lowercase (`'completed'`, `'pending'`, `'confirmed'`) — los miembros Python son `AppointmentStatus.COMPLETED`. -->
<!-- FIX D8: el enum NO tiene `'canceled'` singular. Tiene `'cancelled_by_client'` y `'cancelled_by_detailer'` (British, doble-L). Ver sección de cancel en Plan 21. -->

---

## 2. `GET /api/v1/detailers/me/jobs`

```
Query: ?status=incoming|today|upcoming|completed|canceled&page=1&per_page=20
Auth: JWT (role: detailer)
```

### Response — PaginatedEnvelope

```typescript
{
  "data": [
    {
      "id": "uuid",
      "customer_name": "Jennifer R.",
      "service_name": "Full detail · Q5",
      "location": "Lakeside",
      "scheduled_at": "2026-05-19T08:30:00Z",
      "pay_cents": 17900,
      "status": "completed"
    }
  ],
  "pagination": { "page": 1, "per_page": 20, "total": 142 }
}
```

### Status filter mapping

| Query param | Records |
|---|---|
| `incoming` | Provider not yet accepted |
| `today` | Scheduled for today |
| `upcoming` | Future dates |
| `completed` | Status = completed |
| `canceled` | Status = canceled |

---

## 3. `GET /api/v1/detailers/me/jobs/{id}`

```
Auth: JWT (role: detailer)
```

### Response

```typescript
{
  "id": "uuid",
  "customer": {
    "name": "Jennifer Reyes",
    "phone": "(260) 555-0142",
    "rating": 5.0,
    "total_visits": 14,
    "lifetime_cents": 198600
  },
  "vehicle": {
    "make": "Audi",
    "model": "Q5",
    "year": 2022,
    "color": "white",
    "license_plate": "ABC-1234"
  },
  "service": {
    "name": "Full detail",
    "addons": ["Pet hair", "Clay bar"],
    "price_cents": 17900,
    "duration_min": 150
  },
  "address": {
    "line1": "123 Lake Ave",
    "city": "Fort Wayne",
    "state": "IN",
    "zip": "46802",
    "notes": "Side door entrance"
  },
  "scheduled_at": "2026-05-19T14:00:00Z",
  "status": "confirmed",
  "timeline": [
    { "status": "pending", "at": "2026-05-19T12:00:00Z" },
    { "status": "confirmed", "at": "2026-05-19T12:05:00Z" }
  ]
}
```

---

## 4. `PUT /api/v1/detailers/me/jobs/{id}/accept`

## 5. `PUT /api/v1/detailers/me/jobs/{id}/decline`

```
Auth: JWT (role: detailer)
```

### Request

```json
{}
```

### Response — 200

```json
{
  "status": "accepted"
}
```

### Side effects

- Updates appointment status (FSM: `pending` → `confirmed` / `canceled`)
- Audit log entry
- Push notification to customer
- WebSocket event to appointment room

---

## 6. `GET /api/v1/detailers/me/earnings/summary`

```
Auth: JWT (role: detailer)
```

### Response

```typescript
{
  "pending_cents": 41200,
  "pending_label": "Cash-out available",
  "gross_cents": 864200,
  "gross_label": "This month",
  "lifetime_cents": 4850000,
  "lifetime_label": "All time",
  "breakdown": [
    { "label": "Full detail", "cents": 452000, "color": "#2563eb" },
    { "label": "Interior",    "cents": 198000, "color": "#10b981" },
    { "label": "Exterior",    "cents": 142000, "color": "#f59e0b" },
    { "label": "Add-ons",      "cents": 68000,  "color": "#8b5cf6" },
    { "label": "Tips",         "cents": 4200,   "color": "#ec4899" }
  ],
  "platform_fee_pct": 15,
  "platform_fee_cents": 129630
}
```

### Implementation notes

<!-- FIX D4: la tabla es `services` (no `appointment_services` — esa no existe). El JOIN va por `appointments.service_id` → `services.id`. -->
- `breakdown` aggregates by joining `appointments.service_id` → `services.name` from the service catalog
- `pending_cents` = completed jobs not yet paid out
- `platform_fee_cents` = gross × (platform_fee_pct / 100)

---

## 7. `GET /api/v1/detailers/me/earnings/ledger`

```
Query: ?page=1&per_page=20
Auth: JWT (role: detailer)
```

### Response — PaginatedEnvelope

```typescript
{
  "data": [
    {
      "id": "uuid",
      "date": "2026-05-04",
      "label": "Weekly payout · Chase ••2847",
      "amount_cents": 141820,
      "kind": "out"
    }
  ],
  "pagination": { "page": 1, "per_page": 20, "total": 89 }
}
```

### Kind values

| kind | Meaning |
|---|---|
| `in` | Money received (job completed) |
| `out` | Payout sent to bank |
| `fee` | Platform fee deduction |

---

## 8. `POST /api/v1/detailers/me/earnings/cash-out`

```
Auth: JWT (role: detailer)
Idempotency-Key: required
```

### Request

```json
{
  "amount_cents": 41200
}
```

### Response — 201

```json
{
  "id": "uuid",
  "amount_cents": 41200,
  "status": "pending",
  "estimated_arrival": "2026-05-20"
}
```

### Validation

- Amount cannot exceed `pending_cents`
- Amount must be > 0
- Stripe Connect account must be active
- One pending cash-out at a time

---

## 9. `GET /api/v1/detailers/me/customers`

```
Query: ?filter=all|vip|recent|dormant&page=1&per_page=20
Auth: JWT (role: detailer)
```

### Response — PaginatedEnvelope

```typescript
{
  "data": [
    {
      "id": "uuid",
      "name": "Jennifer Reyes",
      "initials": "JR",
      "avatar_color": "#2563eb",
      "visits": 14,
      "lifetime_cents": 198600,
      "last_visit": "today",
      "is_vip": true,
      "location": "Lakeside",
      "phone": "(260) 555-0142"
    }
  ],
  "top_customers": [
    { "name": "Jennifer Reyes", "lifetime_cents": 198600 }
  ],
  "win_back_targets": [
    { "name": "David Chen", "days_since_last": 42, "lifetime_cents": 89200 }
  ]
}
```

### Filter logic

| Filter | Condition |
|---|---|
| `all` | No filter |
| `vip` | visits >= 10 |
| `recent` | last_visit within 7 days |
| `dormant` | last_visit > 30 days ago |

### Data source

<!-- FIX D3: la columna de fk al cliente es `appointments.client_id` (no `user_id`). -->
Derived from provider's completed appointments, aggregated by `appointments.client_id`.

---

## 10. `GET /api/v1/detailers/me/reviews`

```
Query: ?page=1&per_page=20
Auth: JWT (role: detailer)
```

### Response — PaginatedEnvelope

```typescript
{
  "data": [
    {
      "id": "uuid",
      "customer_name": "Jennifer R.",
      "stars": 5,
      "date": "2 days ago",
      "service_name": "Full detail",
      "body": "Marcus did an incredible job on my Q5...",
      "reply": "Thanks Jennifer! See you next month.",
      "can_reply": true
    }
  ],
  "distribution": [
    { "stars": 5, "count": 312 },
    { "stars": 4, "count": 28 },
    { "stars": 3, "count": 6 },
    { "stars": 2, "count": 1 },
    { "stars": 1, "count": 1 }
  ],
  "highlights": [
    "Mentioned 'thorough' 47 times",
    "Mentioned 'on time' 38 times",
    "Average response time 1.4 min"
  ]
}
```

### Notes

- `highlights` is static initially (computed from keyword analysis in future)
- Filtered to this provider's appointments only

---

## 11. `POST /api/v1/detailers/me/reviews/{id}/reply`

```
Auth: JWT (role: detailer)
```

### Request

```json
{
  "reply": "Thanks Jennifer! See you next month."
}
```

### Response — 200

```json
{
  "id": "uuid",
  "reply": "Thanks Jennifer! See you next month.",
  "replied_at": "2026-05-19T..."
}
```

### Validation

- Max reply length: 2000 chars
- Cannot reply twice to same review

---

## 12. `GET /api/v1/detailers/me/schedule`

```
Query: ?week_start=2026-05-18
Auth: JWT (role: detailer)
```

### Response

```typescript
{
  "working_hours": {
    "monday":    { "start": "09:00", "end": "17:00", "enabled": true },
    "tuesday":   { "start": "09:00", "end": "17:00", "enabled": true },
    "wednesday": { "start": "09:00", "end": "17:00", "enabled": true },
    "thursday":  { "start": "09:00", "end": "17:00", "enabled": true },
    "friday":    { "start": "09:00", "end": "17:00", "enabled": true },
    "saturday":  { "start": null, "end": null, "enabled": false },
    "sunday":    { "start": null, "end": null, "enabled": false }
  },
  "events": [
    {
      "id": "uuid",
      "day": 0,
      "start_hour": 8.5,
      "end_hour": 11,
      "label": "Jennifer R.",
      "service": "Full detail · Q5",
      "type": "booked"
    }
  ],
  "service_zones": [
    { "name": "Lakeside", "radius_mi": 5 }
  ]
}
```

### Event types

| type | Meaning | Color |
|---|---|---|
| `booked` | Confirmed appointment | brand |
| `available` | Open slot | ghost |
| `blocked` | Personal time | warn |
| `hold` | Tentative | warn |

---

## 13. `PUT /api/v1/detailers/me/availability`

```
Auth: JWT (role: detailer)
```

### Request (partial body accepted)

```json
{
  "date": "2026-05-20",
  "working_hours": {
    "monday": { "start": "08:00", "end": "18:00", "enabled": true }
  },
  "blocks": [
    { "date": "2026-05-25", "start_hour": 12, "end_hour": 14, "reason": "lunch" }
  ]
}
```

### Response — 200

```json
{ "status": "updated" }
```

---

## 14. `GET /api/v1/detailers/me/settings`

## 15. `PUT /api/v1/detailers/me/settings`

```
Auth: JWT (role: detailer)
```

### Shared schema

```typescript
{
  "notifications": {
    "new_jobs": true,
    "cancellations": true,
    "reviews": true,
    "payouts": true,
    "marketing": false
  },
  "auto_accept": {
    "max_distance_mi": 10,
    "min_pay_cents": 5000,
    "weekdays_only": true,
    "business_hours_only": true
  },
  "security": {
    "two_factor_enabled": false,
    "session_timeout_min": 60,
    "login_alerts": true
  }
}
```

### Data source

New `provider_settings` table (JSONB column for flexible schema).

---

## 16. Supplies/Inventory

### `GET /api/v1/detailers/me/supplies`

```
Auth: JWT (role: detailer)
```

```typescript
{
  "items": [
    {
      "id": "uuid",
      "name": "Wheel cleaner",
      "stock": 1,
      "par_level": 4,
      "unit": "bottle",
      "cost_cents": 1400,
      "last_ordered": "2026-04-22",
      "supplier": "Chemical Guys",
      "low_stock": true
    }
  ],
  "low_stock_count": 3
}
```

### `POST /api/v1/detailers/me/supplies/{id}/reorder`

```
Auth: JWT (role: detailer)
```

```json
// Request: {}
// Response 201
{ "status": "ordered", "estimated_arrival": "2026-05-22" }
```

---

## 17. Stripe Connect

### `POST /api/v1/detailers/me/connect-account`

```
Auth: JWT (role: detailer, step-up)
```

```typescript
// Response — 201
{
  "url": "https://connect.stripe.com/..."
}
```

### `GET /api/v1/detailers/me/connect-account/status`

```
Auth: JWT (role: detailer)
```

```typescript
{
  "status": "not_started",
  "payouts_enabled": false,
  "charges_enabled": false
}
```

---

## Implementation Order

### Phase 1 — Core provider data (endpoints 1-5)
Dashboard aggregate, jobs, accept/decline

### Phase 2 — Financial (endpoints 6-8, 17)
Earnings summary, ledger, cash-out, Stripe Connect

### Phase 3 — CRM (endpoints 9-11)
Customers, reviews, reply

### Phase 4 — Schedule & Settings (endpoints 12-16)
Schedule, availability, settings, supplies

### Audit
All mutations (accept, decline, cash-out, reply, settings update, reorder) must write audit log.

---

## 17. Operational Requirements

### 17.1 Rate Limiting

| Endpoint | Method | Limit | Burst | Notes |
|----------|--------|-------|-------|-------|
| `/me/dashboard` | GET | 30/min per user | 50 | Aggregate endpoint is query-heavy |
| `/me/jobs` | GET | 60/min per user | 100 | — |
| `/me/jobs/{id}` | GET | 60/min per user | 100 | — |
| `/me/jobs/{id}/accept` | PUT | 20/min per user | 30 | Prevents rapid-fire accept/reject cycles |
| `/me/jobs/{id}/decline` | PUT | 20/min per user | 30 | Same |
| `/me/earnings/summary` | GET | 30/min per user | 50 | — |
| `/me/earnings/ledger` | GET | 30/min per user | 50 | — |
| `/me/earnings/cash-out` | POST | **3/min per user** | 5 | Financial — aggressive rate limit |
| `/me/customers` | GET | 30/min per user | 50 | — |
| `/me/reviews` | GET | 30/min per user | 50 | — |
| `/me/reviews/{id}/reply` | POST | 10/min per user | 15 | — |
| `/me/schedule` | GET | 30/min per user | 50 | — |
| `/me/availability` | PUT | 10/min per user | 15 | — |
| `/me/settings` | GET | 30/min per user | 50 | — |
| `/me/settings` | PUT | 10/min per user | 15 | — |
| `/me/supplies` | GET | 30/min per user | 50 | — |
| `/me/supplies/{id}/reorder` | POST | 5/min per user | 8 | Inventory — prevents accidental bulk orders |
| `/me/connect-account` | POST | 3/min per user | 5 | Stripe — idempotent |
| `/me/connect-account/status` | GET | 30/min per user | 50 | — |

### 17.2 Idempotency Requirements

**CRITICAL: Every mutation must require `Idempotency-Key` header.** The middleware cache key must include the authenticated user's ID to prevent cross-user cache collisions (see audit finding H1 in Plan 22).

| Endpoint | Idempotency-Key | Rationale |
|----------|----------------|-----------|
| `PUT /me/jobs/{id}/accept` | **Required** | Prevents double-accept |
| `PUT /me/jobs/{id}/decline` | **Required** | Prevents double-decline |
| `POST /me/earnings/cash-out` | **Required** | **Financial — prevents double payout** |
| `POST /me/reviews/{id}/reply` | **Required** | Prevents duplicate replies (app-level also enforces one reply) |
| `PUT /me/availability` | Recommended | Prevents duplicate availability updates |
| `PUT /me/settings` | Recommended | Prevents duplicate settings updates |
| `POST /me/supplies/{id}/reorder` | **Required** | Prevents double-order |
| `POST /me/connect-account` | Recommended | Prevents redundant Stripe account creation |

### 17.3 Effective Validation Constraints

| Endpoint | Field | Constraint | Additional |
|----------|-------|-----------|------------|
| `POST /me/earnings/cash-out` | `amount_cents` | int > 0, ≤ `pending_cents`, ≤ 99999999 | **409 Conflict** if pending cash-out exists |
| `POST /me/reviews/{id}/reply` | `reply` | max_length=2000, strip, XSS-sanitized | **409 Conflict** if already replied |
| `PUT /me/availability` | `date` | Must not be in the past | ISO date |
| `PUT /me/availability` | `working_hours.*.start` | Must be < end, 00:00–24:00 | HH:MM format |
| `PUT /me/availability` | `working_hours.*.end` | Must be > start, 00:00–24:00 | HH:MM format |
| `GET /me/customers` | `?filter=` | Enum: `all\|vip\|recent\|dormant` | **Never string interpolation in SQL** |
| `GET /me/jobs` | `?status=` | Enum: `incoming\|today\|upcoming\|completed\|canceled` | — |

### 17.4 Required HTTP Headers

| Header | Source | Details |
|--------|--------|---------|
| `X-Request-ID` | Middleware (existing) | All responses |
| `X-Process-Time` | Middleware | All responses (ms precision) |
| `Idempotency-Key` | Request | **Required** on all mutation endpoints |
| `Retry-After` | Response | On 429 rate-limited responses |

### 17.5 Required Database Migrations

#### Migration M01 — Appointments compound indexes

<!-- FIX D1+D2+D3+D7: nombres ajustados a schema real — detailer_id (no provider_id), client_id (no user_id), estimated_price (sin sufijo _cents), status lowercase. -->

```sql
-- Dashboard aggregate: upcoming jobs sorted by time
CREATE INDEX CONCURRENTLY ix_appointments_detailer_status_time
  ON appointments(detailer_id, status, scheduled_time DESC)
  WHERE is_deleted = FALSE;

-- Earnings aggregation by completed jobs
CREATE INDEX CONCURRENTLY ix_appointments_detailer_completed
  ON appointments(detailer_id, status, completed_at)
  INCLUDE (estimated_price)
  WHERE status = 'completed' AND is_deleted = FALSE;

-- Customer list aggregation
CREATE INDEX CONCURRENTLY ix_appointments_detailer_client
  ON appointments(detailer_id, client_id, status)
  WHERE is_deleted = FALSE;

-- Schedule query: today's route ordered by time
CREATE INDEX CONCURRENTLY ix_appointments_detailer_today
  ON appointments(detailer_id, status, scheduled_time)
  WHERE scheduled_time::date = CURRENT_DATE AND is_deleted = FALSE;
```

#### Migration M02 — Materialized view for earnings breakdown

<!-- FIX D1+D2+D4+D5+D7: detailer_id (no provider_id), estimated_price (no _cents), tabla `services` singular (no services_catalog), appointment_addons.price_cents (no addon_cents), status lowercase. -->

```sql
CREATE MATERIALIZED VIEW mv_provider_earnings_daily AS
SELECT
  a.detailer_id,
  DATE(a.completed_at) AS day,
  COALESCE(s.name, 'Unknown') AS service_name,
  COUNT(*) AS job_count,
  SUM(a.estimated_price) AS total_cents,
  SUM(COALESCE(aa.price_cents, 0)) AS addon_cents
FROM appointments a
LEFT JOIN services s ON a.service_id = s.id
LEFT JOIN appointment_addons aa ON a.id = aa.appointment_id
WHERE a.status = 'completed' AND a.is_deleted = FALSE
GROUP BY a.detailer_id, DATE(a.completed_at), s.name;

CREATE UNIQUE INDEX idx_mv_earnings_daily_unique
  ON mv_provider_earnings_daily(detailer_id, day, service_name);

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_provider_earnings_daily;
```

**Refresh schedule:** Every 15 minutes via worker (not inline).

#### Migration M03 — Stripe Connect onboarding timeout

```sql
ALTER TABLE provider_profiles
  ADD COLUMN stripe_onboarding_expires_at TIMESTAMPTZ,
  ADD COLUMN stripe_onboarding_status VARCHAR(20) DEFAULT 'not_started';
```

### 17.6 Stripe Connect Onboarding Timeout

- `POST /me/connect-account` sets `stripe_onboarding_expires_at = NOW() + INTERVAL '24 hours'`
- Worker runs hourly: `WHERE stripe_onboarding_status = 'pending' AND stripe_onboarding_expires_at < NOW()` → set to `'expired'`
- If detailer requests new URL after expiry: return new onboarding URL (reset timer)

### 17.7 Observability (Prometheus Metrics)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `dashboard_aggregate_duration_ms` | Histogram | provider_id hash (low cardinality) | Dashboard endpoint latency |
| `cash_out_attempts_total` | Counter | status (success/failed) | Cash-out attempts |
| `stripe_connect_errors_total` | Counter | error_type | Stripe onboarding failures |
| `provider_supplies_low_stock` | Gauge | — | Current low-stock count across all providers |
