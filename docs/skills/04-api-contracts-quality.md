# Skill 04: API Contracts Quality

> **Discipline:** API Design & Documentation
> **Applies to:** Any new API contract written as `docs/plans/{NN}-api-contracts-*.md`
> **Source audit:** All 10 findings from `docs/plans/22-security-architecture-audit.md`

---

## Overview

A high-quality contract is the single source of truth for backend implementation, frontend wiring, testing, and security review. This skill defines the SCAM checklist: **S**ecurity, **C**ontracts, **A**udit, **M**etrics.

---

## Prerequisites

- Read `AGENTS.md` — response envelope, pagination envelope, domain structure
- Read `docs/plans/22-security-architecture-audit.md` — understand what went wrong before
- Load skill 01 (security), skill 02 (performance), skill 03 (observability) — they provide the details

---

## SCAM Checklist

### S — Security (cross-ref skill 01)

- [ ] Rate limits specified per endpoint
- [ ] Idempotency requirements stated (required/recommended/not_needed)
- [ ] Auth requirements: role, token type, optional scopes
- [ ] Validation constraints: `max_length`, regex, strip, enum mappings
- [ ] Data exposure review: does response include more than needed?
- [ ] PII handling: encrypted at rest? masked in responses?

### C — Contracts (request/response schemas)

- [ ] Every endpoint has: method, path, query params, request schema, response schema
- [ ] Response uses `Envelope<T>` or `PaginatedEnvelope<T>` wrapper
- [ ] Error responses documented: 400, 404, 409, 422, 429
- [ ] All monetary values explicitly stated as **cents**
- [ ] All datetime values explicitly stated as **ISO 8601 UTC**
- [ ] `nullable` fields clearly marked (optional fields)
- [ ] Response includes example values (not just types)
- [ ] Consumed-by section: which frontend components use this endpoint?

### A — Audit (cross-ref skill 03)

- [ ] Mutations: which audit events are emitted?
- [ ] Metadata: what before/after values are logged?
- [ ] Reads: explicitly stated as "exempt from audit" (no noise)
- [ ] Idempotency key included in audit metadata

### M — Metrics (cross-ref skill 03)

- [ ] Custom Prometheus metrics listed (not just generic HTTP metrics)
- [ ] Business-level metrics: cash-out counters, refund totals, etc.
- [ ] Cache hit-ratio targets for public endpoints
- [ ] SLO targets: p95 latency, error rate

---

## Contract Template

Use this as the base structure for every new contract:

```markdown
# {NN} — API Contracts: {Track Name}

> **Status:** Contract — approved for implementation
> **Priority:** {High/Medium/Low}
> **Design source:** {reference to prototypes}
> **New domain:** {backend path}

## Overview
{2-3 sentence summary}

## Endpoints

### {N}. `{METHOD} {path}`

```
Query: ?param1=type&param2=type
Auth: {None | JWT (role: X)}
Rate limit: {N req/min per IP/user}
Cache: {Cache-Control value | no-store}
Idempotency-Key: {required | recommended | not_needed}
```

#### Request
```json
{exact shape}
```

#### Response — {HTTP status}
```typescript
{exact shape with comments}
```

#### Error responses
| Code | Condition |
|------|-----------|
| 400 | {condition} |
| 409 | {condition} |

#### Validation
| Field | Constraint |
|-------|-----------|
| `name` | max_length=255, strip |

#### Consumed by
- `{Component}` ({page}) — `?{params}`

#### Data source
{Table or aggregation logic}

---

## Operational Requirements

### Rate Limiting
| Endpoint | Limit |
|----------|-------|
| ... | ... |

### Idempotency
| Endpoint | Required |
|----------|----------|
| ... | ... |

### Required Indexes
```sql
...
```

### Observability
| Metric | Labels |
|--------|--------|
| ... | ... |

## Implementation Order

### Phase 1 — ...
### Phase 2 — ...
### Phase 3 — ...
```

---

## Contract Review Process

1. **Author** writes contract following this template
2. **Security reviewer** (skill 01) checks S column
3. **Performance reviewer** (skill 02) checks indexes + cache
4. **Observability reviewer** (skill 03) checks A + M columns
5. **Frontend reviewer** checks consumed-by sections
6. **Final sign-off**: all columns green

---

## Common Pitfalls

| Pitfall | Example | Fix |
|---------|---------|-----|
| No rate limits documented | `// Auth: None` but no rate limit | Always specify rate limit for public endpoints |
| Missing 409 for business rules | Cash-out: "one pending" rule but no 409 | Document every conflict scenario |
| No max_length on text fields | `"name": "string"` | `"name": "string (max 255, strip)"` |
| Ambiguous monetary unit | `"price": 2500` — cents or dollars? | Always suffix: `"price_cents": 2500` |
| No cache strategy | Public endpoint: "Cache: CDN" but no TTL | Explicit `Cache-Control` value |
| Forgetting consumed-by | Endpoint built but no frontend wires it | List every component + page + params |
