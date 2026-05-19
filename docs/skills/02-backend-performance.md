# Skill 02: Backend Performance

> **Discipline:** Database & API Performance
> **Applies to:** Aggregate queries, materialized views, cache strategy, N+1 prevention
> **Source audit:** `docs/plans/22-security-architecture-audit.md` (findings H3, H5)

---

## Overview

RayCarWash backend uses async SQLAlchemy 2.0 with PostgreSQL. The most expensive queries are dashboard aggregates that join 5+ tables. This skill covers indexing strategy, materialized views, Redis caching, and N+1 detection.

---

## Prerequisites

- Read `AGENTS.md` — understand the data model (appointments, providers, users, reviews, vehicles)
- Read `.claude/execution_protocol.md` — OBSERVABILITY step in the pipeline
- Read relevant contract plan sections on indexing (20§17.5, 21§7.5)

---

## Checklist

### 1. Query Analysis (before writing)

- [ ] Identify which endpoints will be query-heavy (dashboard aggregates, reports, earnings)
- [ ] Run `EXPLAIN ANALYZE` on the query during development
- [ ] Check for sequential scans on tables with >10K rows
- [ ] Verify index usage: `Index Scan` vs `Seq Scan` in plan

### 2. Index Design

- [ ] Compound indexes for multi-column WHERE clauses (most selective column first)
  ```sql
  -- GOOD: covers provider_id filter + status filter + time ordering
  CREATE INDEX ix_appointments_provider_status_time
    ON appointments(provider_id, status, scheduled_time DESC)
    WHERE is_deleted = FALSE;
  ```
- [ ] Covering indexes with INCLUDE for aggregate-only columns
  ```sql
  -- GOOD: index-only scan for earnings queries
  CREATE INDEX ix_appointments_provider_completed
    ON appointments(provider_id, status)
    INCLUDE (estimated_price_cents)
    WHERE status = 'COMPLETED' AND is_deleted = FALSE;
  ```
- [ ] Partial indexes with WHERE for filtered queries
- [ ] Avoid over-indexing: max 5-8 indexes per table (write overhead)

### 3. Materialized Views

Use when:
- Query aggregates across thousands of rows
- Data changes infrequently (minutes vs seconds)
- Dashboard/analytics endpoints

```sql
CREATE MATERIALIZED VIEW mv_provider_earnings_daily AS
SELECT provider_id, DATE(completed_at) AS day,
       COUNT(*) AS job_count,
       SUM(estimated_price_cents) AS total_cents
FROM appointments
WHERE status = 'COMPLETED' AND is_deleted = FALSE
GROUP BY provider_id, DATE(completed_at);

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_provider_earnings_daily;
```

**Refresh patterns:**
| Frequency | Use Case |
|-----------|----------|
| Every 15 min | Provider earnings dashboard |
| Every 1 hour | Marketing stats |
| Every 24 hours | Detailer benchmarks |

### 4. Redis Caching Strategy

| Pattern | TTL | Use Case |
|---------|-----|----------|
| `public:{resource}` | 1-24hr | Testimonials, FAQ, coverage zones |
| `provider:{id}:dashboard` | 30s | Dashboard aggregate (user-specific) |
| `provider:{id}:earnings` | 60s | Earnings summary |
| `stats:` | 1hr | Company stats |

**Cache invalidation:**
```python
# After admin CMS update:
await redis.delete("public:testimonials")
await redis.delete("public:faq")
# Pattern-based:
await redis.delete_pattern("stats:*")
```

### 5. N+1 Query Prevention

```python
# WRONG — N+1: 1 query for appointments + N queries for services
appointments = await repo.get_appointments(provider_id)
for a in appointments:
    service = await service_repo.get(a.service_id)  # N queries!

# RIGHT — eager loading:
from sqlalchemy.orm import joinedload
stmt = select(Appointment).options(
    joinedload(Appointment.service),
    joinedload(Appointment.customer)
).where(...)
```

### 6. Pagination

- [ ] Use **cursor-based** pagination for large datasets (appointments with 10K+ rows)
- [ ] Use **offset-based** for admin/small datasets (<1K rows)
- [ ] Always set a `max_per_page` cap (default: 20, max: 100)
- [ ] Return `has_more` boolean for cursor pagination

### 7. Response Compression

- [ ] Enable gzip/brotli compression for JSON responses (already in uvicorn)
- [ ] Large responses (dashboard aggregate) can be 20-50KB — compress

---

## Common Pitfalls

| Pitfall | Impact | Solution |
|---------|--------|----------|
| Missing partial index on `is_deleted = FALSE` | Full table scan on soft-delete queries | Always add `WHERE is_deleted = FALSE` to indexes |
| Sequential scan on provider dashboard | 500ms+ response for providers with 1000+ jobs | Compound index `(provider_id, status, time)` |
| Refreshing materialized view synchronously | API timeout during refresh | Use `CONCURRENTLY` + worker refresh |
| N+1 on review listing | 50 queries for 50 reviews | `selectinload` or `joinedload` |
| No Redis caching on dashboard | Same query 1000 times/day | 30s TTL reduces DB load by 90%+ |
| No max_length on text fields | Storage bloat, slow queries | Always set `max_length` on string fields |

---

## Examples from RayCarWash

### Dashboard aggregate query (optimized)
```python
async def get_dashboard(provider_id: UUID) -> DashboardResponse:
    # Check cache first
    cached = await redis.get(f"provider:{provider_id}:dashboard")
    if cached:
        return DashboardResponse.model_validate_json(cached)

    # Single query with eager loading
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.service),
            joinedload(Appointment.customer),
        )
        .where(
            Appointment.provider_id == provider_id,
            Appointment.is_deleted == False,
            Appointment.scheduled_time >= func.now(),
        )
        .order_by(Appointment.scheduled_time)
        .limit(10)
    )
    result = await session.execute(stmt)
    appointments = result.unique().scalars().all()

    # ... build response ...

    # Cache for 30 seconds
    await redis.set(
        f"provider:{provider_id}:dashboard",
        response.model_dump_json(),
        ex=30,
    )
    return response
```
