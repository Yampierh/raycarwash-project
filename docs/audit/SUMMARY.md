# Audit Discovery Summary

> **Date**: 2026-05-17
> **Total Findings**: ~60 across all layers
> **Scope**: Backend (architecture, domains, infrastructure, tests), Web, Frontend, DevOps

---

## Priority Overview

| Priority | Count | Definition |
|----------|-------|------------|
| **CRITICAL** | 7 | Causes financial loss, security breach, or production crash |
| **HIGH** | 15 | Violates architecture contracts, causes incorrect behavior |
| **MEDIUM** | 20 | Violates best practices, incomplete implementation |
| **LOW** | 18 | Cleanup, documentation, minor improvements |

---

## 🔴 CRITICAL (Must Fix Before Production)

| # | Finding | Category | File(s) |
|---|---------|----------|---------|
| C1 | `PaymentService` inline SQL (bypasses repository) | Architecture | `domains/payments/service.py` |
| C2 | `MatchingService` inline SQL + direct `db.commit()` | Architecture | `domains/matching/service.py` |
| C3 | `write:permissions` on `client` role | Security | `app/db/seed_rbac.py:75` |
| C4 | No `pool_pre_ping` on DB engine (stale connections) | Infrastructure | `infrastructure/db/session.py` |
| C5 | Zero tests for cancellation refund logic | Tests | `test_appointments.py` |
| C6 | Zero tests for double-booking prevention | Tests | `test_appointments.py` |
| C7 | Zero tests for audit logging | Tests | All test files |

## 🟠 HIGH (Must Fix in Current Sprint)

| # | Finding | Category |
|---|---------|----------|
| H1 | `create_all` duplicates migrations in production | Infrastructure |
| H2 | Infrastructure imports from domain (circular risk) | Architecture |
| H3 | No Redis connection pool config | Infrastructure |
| H4 | Empty service files (providers, users, vehicles) | Architecture |
| H5 | `AdminRepository` contains business logic | Architecture |
| H6 | Pricing constants in seed.py instead of shared/ | Architecture |
| H7 | `AppointmentVehicle.vehicle_size` stored (rule violation) | Business Rule |
| H8 | Router-level SQL imports (providers) | Architecture |
| H9 | Zero WebSocket integration tests | Tests |
| H10 | 11 of 18 FSM transitions untested | Tests |
| H11 | Zero tests for failure modes (Stripe/DB) | Tests |
| H12 | Sprint 9 admin extensions have zero tests | Tests |
| H13 | `web/AGENTS.md` references non-existent docs | Web |
| H14 | Web login doesn't handle backend envelope | Web |
| H15 | Email SMTP — no retry, narrow exception catch | Infrastructure |

## 🟡 MEDIUM (Fix in Next Sprint)

| # | Finding | Category |
|---|---------|----------|
| M1 | `Envelope[T]` compliance gaps (7 legacy routers) | Architecture |
| M2 | AuthService directly mutates User model | Architecture |
| M3 | `datetime.utcnow()` instead of timezone-aware | Bug |
| M4 | Missing repositories (Payments, Matching, ClientProfile) | Architecture |
| M5 | S3/Twilio/Google Maps adapters not implemented | Infrastructure |
| M6 | `db.commit()` inside H3 infrastructure | Architecture |
| M7 | Cross-domain direct coupling (reviews→providers) | Architecture |
| M8 | Soft delete verification not tested | Tests |
| M9 | Vehicle body_class/size mapping not tested | Tests |
| M10 | `map_body_to_size` in wrong location | Infrastructure |
| M11 | No server-side auth in web admin | Security |
| M12 | Empty `next.config.ts` | Web |
| M13 | Button variant docs mismatch (outline vs cta) | Docs |
| M14 | Hardcoded IPs in frontend config | Frontend |
| M15 | Stale documentation (screens, services counts) | Docs |
| M16 | Integration plans stuck on "Planning" | Docs |
| M17 | `warnings.warn` instead of `logger.warning` | Infrastructure |
| M18 | fakeredis fallback masks parity issues | Infrastructure |
| M19 | Missing `SEARCHING`/`NO_DETAILER_FOUND` FSM entries | Architecture |
| M20 | `estimated_price` / `actual_price` immutability untested | Tests |

## ⚪ LOW (Nice to Have)

| # | Finding |
|---|---------|
| L01 | `app.state` assignment dicts not shared across workers |
| L02 | `IdempotencyMiddleware` sees `request.state.user` as potentially missing |
| L03 | `_get_encryption_key()` late failure pattern |
| L04 | `float("inf")` in Pydantic settings may not serialize |
| L05 | Seed functions run on every startup (unnecessary in prod) |
| L06 | Google audience verification skipped when `GOOGLE_CLIENT_ID` empty |
| L07 | `RAYCARWASH_ENV` defaults to `development` |
| L08 | New NHTSA `httpx.AsyncClient` per call |
| L09 | No NHTSA retry for transient failures |
| L10 | No Stripe retry for transient API failures |
| L11 | Inline imports in AuthService method bodies |
| L12 | `__dict__` manipulation in AppointmentService |
| L13 | `STORAGE_ADAPTER` raises `RuntimeError` in production |
| L14 | No postinstall hook for frontend setup |
| L15 | `npm run dev` omits web dashboard |
| L16 | `install-deps` uses POSIX path for venv |
| L17 | No backend service in docker-compose |
| L18 | Redis without persistence in docker-compose |

---

## File Reference

| File | Content |
|------|---------|
| `01-architecture-violations.md` | All architecture, execution protocol, DDD violations |
| `02-test-gaps.md` | All test coverage gaps and test suite health |
| `03-infrastructure-issues.md` | All infrastructure findings (DB, Redis, Email, etc.) |
| `04-web-frontend-issues.md` | All web, frontend, docs, and devops issues |
| `SUMMARY.md` | This file — master index of all findings |

---

## Remediation Plan

All P0/P1 findings from this audit are tracked in [`docs/plans/08-hardening.md`](../plans/08-hardening.md), organized in 5 execution phases:

| Phase | Focus | Timeline |
|-------|-------|----------|
| Phase 0 | Inmediatos (pool_pre_ping, RBAC, create_all guard, Redis config) | Week 1 |
| Phase 1A→1B | Web login envelope -> EnvelopeRouter roll-out | Week 2 |
| Phase 2 | Service layer reorg (AdminService, PaymentsRepo, MatchingRepo) | Week 3 |
| Phase 3 | DB migrations (estimated_price_cents, BigInteger, dedup columns) | Week 4 |
| Phase 4 | Tests (refunds, double-booking, FSM, WebSocket, failure modes) | Week 5 |

## Next Steps

1. **Prioritize**: Select items from Critical > High for the execution plan
2. **Decompose**: Each finding may require multiple implementation steps
3. **Apply execution_protocol.md**: For each fix, follow ARCHITECTURE > CONTRACTS > DOMAIN SKILL > IMPLEMENTATION > OBSERVABILITY > VALIDATION
4. **Re-validate**: After fixes, run full test suite and envelope compliance check

> **Full traceability matrix**: See [`docs/INDEX.md`](../INDEX.md) section 4 for audit finding -> plan mapping.
