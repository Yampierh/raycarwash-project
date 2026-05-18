# Test Coverage Gaps Analysis

> **Date**: 2026-05-17
> **Scope**: All `backend/tests/` — ~24 files, ~200+ test cases
> **Legend**: ✅ Covered | ⚠️ Partial | ❌ Missing

---

## 1. CRITICAL GAPS

### 1.1 Cancellation Refund Logic — ❌ ZERO TESTS

**Business rule**: `>=24h 100% · 2-24h 50% · <2h 0%`

**Implementation**: `backend/domains/appointments/service.py` lines 530-605

**Untested scenarios**:
| Scenario | Refund | Risk |
|----------|--------|------|
| Cancel CONFIRMED >=24h before | 100% | Financial loss if buggy |
| Cancel CONFIRMED 2-24h before | 50% | Wrong refund amount |
| Cancel CONFIRMED <2h before | 0% | Unauthorized refund |
| Auth void vs captured payment | Varies | Stripe API errors |
| `stripe_refund_id` populated | — | Audit trail integrity |
| Audit log entries for refund | — | Compliance failure |

**The only cancellation test** (`test_status_cancel_by_client` at `test_appointments.py:543`) tests PENDING → CANCELLED_BY_CLIENT, which never enters the refund path (appointment not yet paid).

### 1.2 Double-Booking Prevention — ❌ ZERO TESTS

**Mechanism**: `pg_advisory_xact_lock` in `AppointmentRepository._detailer_lock_key()` (lines 44-53)

**Untested**:
- Two overlapping appointments for same detailer → one rejected
- UUID-to-int64 key conversion (`_detailer_lock_key`)
- Lock released after transaction ends
- Race condition with concurrent requests
- `get_overlapping_count()` interval overlap formula

### 1.3 Audit Logging — ❌ ZERO TESTS

**Architecture mandate**: "Audit log every mutation"

**Zero tests verify**:
- That any mutation produces an audit log entry
- Audit log contains correct actor, action, resource_id, details
- Audit log is append-only (no deletes)
- Failed mutations do NOT produce audit entries

### 1.4 Stripe / Infrastructure Failure Modes — ❌ ZERO TESTS

**Adapter is fully stubbed**. No tests for:
- Stripe API returns error / rate limit / is down
- SMTP send fails (email silently lost)
- NHTSA API returns 5xx
- Redis is unavailable (beyond idempotency)
- DB connection loss / pool exhaustion
- 5MB body size limit enforcement

---

## 2. HIGH PRIORITY GAPS

### 2.1 WebSocket — ❌ ZERO INTEGRATION TESTS

**File**: `conftest.py` lines 110-114 — fully mocked via `MagicMock()`

**Untested**:
- Connection with JWT in query param
- Heartbeat (30s ping/pong)
- Exponential backoff reconnection
- Close codes: 4001 (unauthorized), 4003 (forbidden), 4004 (not found)
- `status_change` and `location_update` message delivery
- Multiple concurrent connections

### 2.2 State Machine — ⚠️ 11 of 18 Transitions Untested

**Tested** (7 of 18):
- PENDING → CONFIRMED ✅
- PENDING → CANCELLED_BY_CLIENT ✅
- CONFIRMED → IN_PROGRESS ✅
- IN_PROGRESS → COMPLETED ✅
- COMPLETED → (any) [rejected] ✅
- Invalid PENDING → COMPLETED ✅
- COMPLETED with actual_price ✅

**Not tested** (11):
| Transition | Notes |
|-----------|-------|
| PENDING → CANCELLED_BY_DETAILER | Need intent from detailer |
| CONFIRMED → ARRIVED | Basic flow |
| CONFIRMED → CANCELLED_BY_CLIENT | Before arrival |
| CONFIRMED → CANCELLED_BY_DETAILER | Detailer cancels confirmed |
| ARRIVED → IN_PROGRESS | Core flow |
| ARRIVED → CANCELLED_BY_CLIENT | Client cancels after arrival |
| ARRIVED → CANCELLED_BY_DETAILER | Detailer cancels after arrival |
| IN_PROGRESS → NO_SHOW | Detailer marks no-show |
| CANCELLED_BY_CLIENT → (any) | Terminal state |
| CANCELLED_BY_DETAILER → (any) | Terminal state |
| NO_SHOW → (any) | Terminal state |
| SEARCHING / NO_DETAILER_FOUND states | Entire states untested |

### 2.3 Sprint 9 Admin Extensions — ❌ ZERO TESTS

**AGENTS.md acknowledges**: "Sprint 9 admin extensions (appointments/verifications/payments) ship without dedicated tests."

No tests for:
- Admin appointment management (force status, list, cancel)
- Admin verification review (approve, reject, list pending)
- Admin payment management (view transactions, refunds)

---

## 3. MEDIUM PRIORITY GAPS

### 3.1 Soft Delete Verification — ⚠️ Tests Only Check HTTP Status

| Entity | Test Verifies HTTP 204 | Test Verifies DB State |
|--------|----------------------|----------------------|
| Vehicle (test_vehicles.py:311) | ✅ (assert 204) | ❌ |
| Payment Method (test_payment_methods:262) | ✅ | ✅ (checks listing) |
| User (test_admin) | ❌ | ❌ |
| Appointment | ❌ | ❌ |
| Address | ❌ | ❌ |

No test explicitly verifies `is_deleted=True`, `deleted_at` populated, or that soft-deleted rows are filtered from queries.

### 3.2 Vehicle Body Class / Size Mapping — ❌ ZERO TESTS

`map_body_to_size()` is a key business function in `infrastructure/nhtsa/client.py` lines 21-41.

No test verifies:
- Sedan → SMALL
- SUV → LARGE
- Truck → XLARGE
- Unknown body class → MEDIUM (default)
- edge cases: `body_class` casing, whitespace

### 3.3 `estimated_price` Immutability — ❌ ZERO TESTS

No test verifies that `estimated_price` cannot change after appointment creation.

### 3.4 `actual_price` Set-Once on COMPLETED — ❌ ZERO TESTS

No test verifies that `actual_price` is immutable after COMPLETED state.

### 3.5 VIN Lookup Flaky Test

**File**: `test_vehicles.py:269`

```python
assert response.status_code in [200, 404]  # Accepts failure!
```

Depends on external NHTSA API with no mock. Test passes even if API is down.

### 3.6 Matching Tests — ⚠️ Conditional Assertions

**File**: `test_matching.py:231`

```python
if len(data) > 0:  # Skips assertions if empty
```

Several tests skip assertions when results are empty, masking potential failures.

---

## 4. TEST SUITE HEALTH

### Hardcoded Values

| Value | Count | Risk |
|-------|-------|------|
| `"Test1234!"` | ~15+ files | Password policy change breaks all |
| `41.0793, -85.1394` | 4 files | Fort Wayne coordinates — fine |
| `"testclient@example.com"` | ~8 files | Coupled to fixture |
| `"2027-06-15T10:00:00Z"` | 3 files | Far-future date, valid til 2027 |
| `"00000000-0000-0000-0000-000000000000"` | 2 files | Null UUID — fine |

### Flaky Tests

| Test | File:Line | Reason |
|------|-----------|--------|
| `test_vin_lookup_valid` | `test_vehicles.py:269` | External API dependency |
| `test_matching_response_structure` | `test_matching.py:231` | Conditional assertions |
| `test_lockout_self_expires` | `test_auth.py:1187` | Race condition with 1s |
| `test_reset_expired_token_rejected` | `test_auth.py:772` | Manual backdated token |

---

## Summary — Priority Matrix

| Priority | What | Effort | Impact |
|----------|------|--------|--------|
| P0 | Cancellation refund tests | 2-3 days | Financial correctness |
| P0 | Double-booking prevention tests | 1 day | Data integrity |
| P0 | Audit logging tests | 1 day | Compliance |
| P1 | FSM transition coverage (11 missing) | 2 days | Business logic |
| P1 | WebSocket integration tests | 2 days | Real-time reliability |
| P1 | Stripe/DB failure mode tests | 2 days | Production resilience |
| P1 | Sprint 9 admin tests | 1-2 days | Regression protection |
| P2 | Soft delete verification | 0.5 day | Data integrity |
| P2 | `map_body_to_size` tests | 0.5 day | Core business logic |
| P2 | Fix flaky tests | 1 day | CI reliability |
