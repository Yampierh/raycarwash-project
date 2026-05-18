# RFC: Auth, Idempotency, and Appointments System Hardening

## Status
Draft

## Authors
[Your Name]

## Reviewers
TBD

## Created
2026-05-17

---

# 1. Context

The current system is transitioning from MVP-level reliability to production-grade infrastructure. Recent design reviews have identified several risks across authentication, idempotency, data consistency, and query scalability.

This RFC proposes a set of changes to ensure:

- Strong consistency under concurrency
- Deterministic idempotency behavior
- Proper separation of concerns
- Scalable data access patterns
- Operational safety during migrations

---

# 2. Goals

## Primary Goals

- Prevent race conditions in authentication flows
- Guarantee correctness of idempotent operations
- Ensure safe schema evolution with backfills
- Improve scalability of high-read endpoints
- Decouple transport layer from domain logic

## Non-Goals

- Full auth system redesign
- Migration to a different database
- Rewriting existing APIs

---

# 3. Problem Areas

## 3.1 Refresh Token Concurrency

### Problem
Concurrent refresh requests can result in multiple valid tokens due to non-atomic version handling.

### Impact
- Session inconsistency
- Security risk (token reuse)

---

## 3.2 Idempotency Without Payload Binding

### Problem
Idempotency keys are not tied to request payloads.

### Impact
- Incorrect cached responses
- Financial inconsistencies in payment flows

---

## 3.3 Missing Backfill Strategy

### Problem
Schema changes do not include data backfills.

### Impact
- Null/invalid data in production
- Broken queries and analytics

---

## 3.4 Transport Leakage into Domain Layer

### Problem
Framework-specific objects (e.g., request state) are accessed inside service layer.

### Impact
- Reduced testability
- Tight coupling

---

## 3.5 Ambiguous Step-Up Authentication State

### Problem
Step-up authentication success is implicit rather than event-driven.

### Impact
- Inconsistent authorization decisions
- Difficult auditing

---

## 3.6 Appointment History Query Scalability

### Problem
Deep pagination with joins leads to performance degradation.

### Impact
- Slow response times
- Database load spikes

---

# 4. Proposed Solutions

## 4.1 Atomic Refresh Token Rotation

### Solution
Use atomic version increment at DB level.

### Example

```sql
UPDATE refresh_token_families
SET version = version + 1
WHERE user_id = ? AND family_id = ?
RETURNING version;
```

### Result
- Eliminates race conditions
- Ensures single valid token version

---

## 4.2 Payload-Bound Idempotency Keys

### Solution
Include request body hash in idempotency key.

### Example

```python
cache_key = f"idemp:{user_id}:{endpoint}:{body_hash}"
```

### Result
- Prevents incorrect cache reuse
- Guarantees deterministic responses

---

## 4.3 Explicit Backfill Strategy

### Solution

- Create idempotent backfill scripts
- Run via background jobs or migration pipeline

### Requirements

- Retry-safe
- Observable (logs/metrics)

### Result

- Data consistency across versions
- Safe production rollouts

---

## 4.4 Introduce AuditContext Boundary

### Solution

Pass explicit context object into services.

### Example

```python
class AuditContext:
    user_id: str
    request_id: str
```

### Result

- Decouples framework from domain
- Improves testability

---

## 4.5 Step-Up Authentication Event

### Solution

Introduce explicit domain event:

- step_up_succeeded

### Result

- Clear auth state transitions
- Improved auditability

---

## 4.6 Scalable Appointment History

### Solution Options

1. Materialized View
2. Hybrid Storage (hot vs cold data)
3. Cursor-based pagination

### Recommended Approach

- Cursor pagination (short term)
- Materialized view (long term)

### Result

- Predictable query performance
- Reduced DB load

---

# 5. Prioritization

| Area | Impact | Urgency | Phase |
|------|--------|--------|------|
| Refresh Token Concurrency | High | Immediate | Phase 1 |
| Idempotency Payload Binding | High | Immediate | Phase 1 |
| Backfill Strategy | High | Immediate | Phase 1 |
| Audit Context Refactor | Medium | Short-term | Phase 2 |
| Step-Up Event | Medium | Medium | Phase 2 |
| Appointment Scalability | Low | Later | Phase 3 |

---

# 6. Risks & Mitigations

| Risk | Mitigation |
|-----|-----------|
| Migration failures | Idempotent scripts + rollback plan |
| Increased complexity | Documentation + clear interfaces |
| Performance regressions | Load testing before rollout |

---

# 7. Open Questions

- Should refresh tokens support multi-device isolation?
- Do we need global idempotency guarantees across services?
- What is the retention policy for historical appointments?

---

# 8. Rollout Plan

## Phase 1 (Critical Fixes)

- Token rotation fix
- Idempotency improvements
- Backfill execution

## Phase 2 (Structural Improvements)

- Audit context refactor
- Step-up event

## Phase 3 (Scalability)

- Appointment query optimization

---

# 9. Success Metrics

- Zero duplicate refresh token issuance
- Zero idempotency-related inconsistencies
- Backfill completion rate = 100%
- P95 latency improvement for history endpoint

---

# 10. Conclusion

These changes elevate the system from functional correctness to production-grade reliability. The focus is on preventing real-world failures rather than improving theoretical design.

Approval of this RFC is recommended before scaling traffic or introducing payment-critical flows.

