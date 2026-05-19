# 19 — API Contracts: Track 1 — Marketing Public Endpoints

> **Status:** Contract — approved for implementation
> **Priority:** High
> **Design source:** `raycarwash/project/` prototypes — Landing, Customer, Detailers, Mechanic pages
> **New domain:** `backend/domains/public/` (router + schemas + services + repository)

---

## Overview

9 new public endpoints serving dynamic content for marketing landing pages. All are **read-only except** contact form + waitlist join. Cache-friendly (CDN, 1hr stale-while-revalidate).

---

## 1. `GET /api/v1/public/testimonials`

```
Query: ?role=client|detailer&limit=4&featured=true
Auth: None
Cache: CDN, 1hr
```

### Response schema

```typescript
// Envelope<TestimonialsResponse>
{
  "testimonials": [
    {
      "id": "uuid",
      "quote": "Booked at 9 a.m., the truck was in my driveway by 11.",
      "name": "Maria G.",
      "city": "Fort Wayne, IN",
      "rating": 5,
      "role": "client",           // "client" | "detailer"
      "meta": null,                // optional: "Detailer · 312 jobs · ★ 4.9"
      "featured": true,
      "sort_order": 1,
      "created_at": "2026-01-15T..."
    }
  ]
}
```

### Filtering

| Parameter | Type | Default | Description |
|---|---|---|---|
| `role` | `"client" \| "detailer"` | `null` (both) | Filter by role |
| `limit` | `int` | `10` | Max items |
| `featured` | `bool` | `false` | Only featured |

### Consumed by

- `Testimonials` (landing page) — `?role=client&limit=4&featured=true`
- `ReviewsWall` (customer page) — `?role=client&limit=8&featured=true`
- `DetTestimonials` (detailers page) — `?role=detailer&limit=3&featured=true`

### Data source

New `testimonials` table (seeded with current hardcoded testimonials from prototypes).

```sql
CREATE TABLE testimonials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(255),
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    role VARCHAR(20) NOT NULL CHECK (role IN ('client', 'detailer')),
    meta VARCHAR(255),
    featured BOOLEAN DEFAULT false,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Test data (seed)

Use the 4 testimonials from `sections-b.jsx` (Maria G., Derrick P., Jonas R., Anna L.) + 8 from `customer-b.jsx` ReviewsWall + 3 from `detailers-b.jsx` DetTestimonials.

---

## 2. `GET /api/v1/public/faq`

```
Query: ?category=rider|detailer|mechanic|provider
Auth: None
Cache: CDN, 1hr
```

### Response schema

```typescript
// Envelope<FaqResponse>
{
  "faq": [
    {
      "id": "uuid",
      "category": "rider",
      "question": "What area do you serve?",
      "answer": "Fort Wayne, IN and surrounding suburbs...",
      "sort_order": 1
    }
  ]
}
```

### Consumed by

- `FAQ` (landing) — `?category=rider`
- `CustFAQ` (customer page) — `?category=rider`
- `DetFAQ` (detailers page) — `?category=detailer`
- `MechFAQ` (mechanic page) — `?category=mechanic`
- `ViewHelp` (provider dashboard) — `?category=provider`

### Data source

New `faq` table. Seed with all FAQ items from sections-b, customer-b, detailers-b, mechanic, and dash-services.

---

## 3. `GET /api/v1/public/coverage-zones`

```
Auth: None
Cache: CDN, 24hr
```

### Response schema

```typescript
{
  "zones": [
    {
      "name": "Fort Wayne",
      "is_primary": true,
      "svg": { "cx": 50, "cy": 50, "r": 12 }
    },
    {
      "name": "Aboite",
      "is_primary": false,
      "svg": { "cx": 30, "cy": 58, "r": 6 }
    },
    {
      "name": "Huntertown",
      "is_primary": false,
      "svg": { "cx": 48, "cy": 28, "r": 5 }
    },
    {
      "name": "Leo-Cedarville",
      "is_primary": false,
      "svg": { "cx": 68, "cy": 30, "r": 5 }
    },
    {
      "name": "New Haven",
      "is_primary": false,
      "svg": { "cx": 70, "cy": 56, "r": 6 }
    },
    {
      "name": "Waynedale",
      "is_primary": false,
      "svg": { "cx": 40, "cy": 70, "r": 4 }
    }
  ]
}
```

### Consumed by

`Coverage` component (landing page) — renders SVG map with labeled city circles.

### Data source

New `coverage_zones` table or static config. SVG coordinates are in a 100×100 viewBox.

---

## 4. `POST /api/v1/public/coverage/check`

```
Auth: None
Rate limit: 30 req/min per IP
```

### Request

```json
{
  "zip": "46802"
}
```

### Response — ZIP covered

```json
{
  "covered": true,
  "eta_at_launch": "~22 min",
  "zone": "Fort Wayne"
}
```

### Response — ZIP not covered

```json
{
  "covered": false,
  "eta_at_launch": null,
  "zone": null
}
```

### Logic

1. Look up ZIP in `coverage_zips` table
2. If found → return zone name + ETA
3. If not found → return `covered: false`
4. Future: integrate with H3 geofencing in `infrastructure/h3/`

### Data source

New `coverage_zips` table (ZIP → zone mapping):
```sql
CREATE TABLE coverage_zips (
    zip VARCHAR(5) PRIMARY KEY,
    zone_name VARCHAR(255) NOT NULL,
    eta_min INTEGER,
    is_active BOOLEAN DEFAULT true
);
```

Seed with: 46802, 46804, 46805, 46807, 46815 + any others.

---

## 5. `GET /api/v1/public/stats`

```
Auth: None
Cache: CDN, 1hr
```

### Response schema

```typescript
{
  "deliveries": 2400,
  "deliveries_label": "2,400+",
  "avg_eta_min": 22,
  "avg_eta_label": "22 min",
  "avg_rating": 4.9,
  "avg_rating_label": "4.9★",
  "active_detailers": 85,
  "active_detailers_label": "85",
  "median_earnings_per_hr": 42,
  "median_earnings_label": "$42/hr",
  "total_reviews": 1240,
  "total_reviews_label": "1,240+"
}
```

### Consumed by

`Hero` component (landing page) — stat counters change by audience toggle.

### Data source

Aggregated from real data:
- `deliveries` → `SELECT COUNT(*) FROM appointments WHERE status = 'completed'`
- `avg_eta_min` → avg time from booking to assigned
- `avg_rating` → FROM `reviews`
- `active_detailers` → `SELECT COUNT(*) FROM provider_profiles WHERE is_active = true`
- `total_reviews` → `SELECT COUNT(*) FROM reviews`

---

## 6. `GET /api/v1/public/stats/detailer-benchmarks`

```
Auth: None
Cache: CDN, 24hr
```

### Response schema

```typescript
{
  "median_weekly": 1840,
  "median_weekly_label": "$1,840 / wk",
  "top_quartile_weekly": 2720,
  "top_quartile_weekly_label": "$2,720 / wk",
  "top_10pct_weekly": 3400,
  "top_10pct_weekly_label": "$3,400+ / wk",
  "avg_per_job": 112,
  "avg_per_job_label": "$112"
}
```

### Consumed by

- `ForDetailersSplit` — earnings card stat blocks
- `EarningsCalc` — benchmark reference values

### Data source

Static config initially (marketing-approved numbers). Future: real aggregation from actual detailer earnings.

---

## 7. `POST /api/v1/public/contact`

```
Auth: None
Rate limit: 5 req/min per IP
Idempotency-Key: optional
```

### Request

```json
{
  "name": "string (required, max 255)",
  "email": "string (required, valid email)",
  "subject": "string (optional, max 255)",
  "message": "string (required, max 5000)"
}
```

### Response — 201

```json
{
  "id": "uuid",
  "status": "received"
}
```

### Side effects

1. Insert into `contact_submissions` table
2. Send internal notification email to support team

### Error responses

| Code | Condition |
|---|---|
| 422 | Validation error (missing/invalid fields) |
| 429 | Rate limit exceeded |

---

## 8. `POST /api/v1/public/waitlist/join`

```
Auth: None
Rate limit: 3 req/min per IP
```

### Request

```json
{
  "email": "string (required, valid email)",
  "role": "mechanic"
}
```

### Response — 201

```json
{
  "id": "uuid",
  "position": 348
}
```

### Logic

1. Check email not already on waitlist (idempotent — return 409 if duplicate)
2. Insert into `waitlist_entries` table
3. Return position (current count + 1)

### Data source

New `waitlist_entries` table:
```sql
CREATE TABLE waitlist_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL DEFAULT 'mechanic',
    position INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 9. `GET /api/v1/public/waitlist/count`

```
Auth: None
Cache: CDN, 30s
```

### Response schema

```typescript
{
  "count": 347,
  "avg_wait_weeks": "4 weeks"
}
```

### Consumed by

- `MechHero` — auto-refreshing counter
- `MechCTA` — "347 people ahead of you" text

---

## Implementation Order

### Phase 1 — Data layer (all 9 endpoints)
1. Create `domains/public/models.py` — SQLAlchemy models
2. Create `domains/public/schemas.py` — Pydantic request/response schemas
3. Create migration files (alembic)
4. Create seed data (from prototype hardcoded values)

### Phase 2 — Backend endpoints
5. Create `domains/public/repository.py`
6. Create `domains/public/service.py`
7. Create `domains/public/router.py`
8. Mount router in `api/router.py`

### Phase 3 — Portal wiring
9. Update each portal component to SWR-fetch from new endpoints
10. Add fallback to i18n hardcoded data while loading

### Audit rules
All mutations (contact, waitlist) must write audit log. Reads are exempt.

---

## 10. Operational Requirements

### 10.1 Rate Limiting

| Endpoint | Method | Limit | Burst | Applied Via |
|----------|--------|-------|-------|-------------|
| `/public/testimonials` | GET | 60/min per IP | 100 | slowapi |
| `/public/faq` | GET | 60/min per IP | 100 | slowapi |
| `/public/coverage-zones` | GET | 30/min per IP | 50 | slowapi |
| `/public/coverage/check` | POST | **10/min per IP** | 15 | slowapi (mitigates ZIP enumeration) |
| `/public/stats` | GET | 60/min per IP | 100 | slowapi |
| `/public/stats/detailer-benchmarks` | GET | 60/min per IP | 100 | slowapi |
| `/public/contact` | POST | **3/min per IP, 20/day per email** | 5 | slowapi + Redis counter per email |
| `/public/waitlist/join` | POST | **3/min per IP** | 5 | slowapi (mitigates email harvesting) |
| `/public/waitlist/count` | GET | 30/min per IP | 50 | slowapi |

All rate-limited responses must include `Retry-After` header.

### 10.2 Cache Strategy (Redis + CDN)

| Endpoint | Cache-Control | CDN TTL | ETag | Invalidation Trigger |
|----------|--------------|---------|------|---------------------|
| `/public/testimonials` | `public, max-age=3600, stale-while-revalidate=300` | 1hr | Yes | Admin CMS: testimonial change |
| `/public/faq` | `public, max-age=3600, stale-while-revalidate=300` | 1hr | Yes | Admin CMS: FAQ change |
| `/public/coverage-zones` | `public, max-age=86400, stale-while-revalidate=3600` | 24hr | Yes | Admin: zone config change |
| `/public/stats` | `public, max-age=3600, stale-while-revalidate=300` | 1hr | No | Internal: daily recompute |
| `/public/stats/detailer-benchmarks` | `public, max-age=86400, stale-while-revalidate=3600` | 24hr | No | Marketing: manual update |
| `/public/waitlist/count` | `public, max-age=30` | 30s | No | Real-time: new signup |

Non-cacheable endpoints (contact, waitlist/join, coverage/check): set `Cache-Control: no-store`.

### 10.3 Idempotency Requirements

| Endpoint | Idempotency-Key | Notes |
|----------|----------------|-------|
| `POST /public/contact` | Recommended | Prevents duplicate support tickets |
| `POST /public/waitlist/join` | Recommended | Prevents duplicate waitlist entries (email unique constraint also catches this) |

### 10.4 Effective Validation Constraints

Every string input field must have these Pydantic validators:

**All endpoints:**
```python
Field(..., max_length=255, strip_whitespace=True)
```

| Endpoint | Field | Additional Validation |
|----------|-------|----------------------|
| `POST /contact` | `name` | max_length=255, strip |
| `POST /contact` | `email` | max_length=320, EmailStr (lowercase + strip) |
| `POST /contact` | `subject` | max_length=255, strip, optional |
| `POST /contact` | `message` | max_length=5000, strip, XSS-sanitized |
| `POST /waitlist/join` | `email` | max_length=320, EmailStr (lowercase + strip), unique |
| `POST /waitlist/join` | `role` | Enum: `mechanic\|detailer\|provider`, default `mechanic` |

### 10.5 Required HTTP Headers

| Header | Source | All Endpoints |
|--------|--------|---------------|
| `X-Request-ID` | Middleware (existing) | Always |
| `X-Process-Time` | Middleware | Always (ms precision) |
| `X-Cache` | Response | Public GET endpoints only (HIT/MISS/DYNAMIC) |
| `Retry-After` | Response | Only on 429 rate-limited responses |
| `Cache-Control` | Response | As specified in 10.2 |

### 10.6 Observability (Prometheus Metrics)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | endpoint, method, status | Total requests per endpoint |
| `http_request_duration_ms` | Histogram | endpoint, method | Latency p50/p95/p99 |
| `rate_limit_exceeded_total` | Counter | endpoint, ip_hash | Rate limit triggers |
| `public_cache_hit_ratio` | Gauge | endpoint | Cache hit ratio per endpoint |

### 10.7 CORS Hardening

- Allowed origins: portal domain + admin domain (production)
- Allowed methods: GET, POST, OPTIONS (no PUT/PATCH/DELETE on public endpoints)
- Max age: 86400
- Credentials: false (public endpoints don't need cookies)
