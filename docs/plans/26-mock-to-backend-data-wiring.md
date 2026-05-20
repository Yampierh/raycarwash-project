# 26 — Mock → Backend Data Wiring

> **Status:** Planning
> **Priority:** High
> **Dependencies:** [`25-designer-to-next-frontend.md`](./25-designer-to-next-frontend.md) (creates the `lib/mock/*.ts` seams this plan consumes) · [`08-hardening.md`](./08-hardening.md) Phase 0 · [`23-auth-hardening.md`](./23-auth-hardening.md) Fase 1
> **Soft deps (per surface):** [11](./11-provider-dashboard.md), [13](./13-customer-dashboard.md), [14](./14-mechanic-vertical.md), [24](./24-auth-pages-and-admin-dashboard.md), [20](./20-api-contracts-track2-provider-dashboard.md), [21](./21-api-contracts-track3-customer-dashboard.md)
> **Out of scope:** anything that changes the *visual layer* — Plan 25 owns that. This plan only swaps `import { MOCK_X } from "@/lib/mock/X"` for a real fetcher.
> **Mandatory pipeline:** every change MUST follow [`.claude/execution_protocol.md`](../../.claude/execution_protocol.md) — ARCHITECTURE → CONTRACTS → DOMAIN SKILL → IMPLEMENTATION → OBSERVABILITY → VALIDATION.
> **Skill:** [`~/.claude/skills/backend/mock_to_backend.md`](file://C:/Users/yampi/.claude/skills/backend/mock_to_backend.md) — codifies the protocol used here so every future mock→backend swap follows the same flow.

---

## 1. Why this plan exists

Plan 25 lands all Designer screens running on hardcoded data in `lib/mock/*.ts`. Every export there `satisfies` either a real type from `@/lib/api/types.ts` or a placeholder flagged `TODO(plan-NN)`. This plan **picks up exactly at that seam** and:

1. Walks every `MOCK_*` export.
2. Confirms the contract (envelope shape, fields, sort, filters, pagination, idempotency) against existing API design or existing per-surface plans (11/13/24).
3. Implements the missing endpoint(s) in the backend following the project's mandatory pipeline.
4. Adds the typed fetcher hook in the frontend (`lib/hooks/*` for portal, `lib/api.ts` for admin).
5. Swaps the import in the route file: `MOCK_X` → `useX()` / `await getX()`.
6. Deletes the mock export. When a `lib/mock/*.ts` file is empty, deletes the file.

When the file is gone, the surface is **fully wired**. When *every* file under `lib/mock/` is gone, this plan is done.

This plan is the **mirror** of Plan 25. Plan 25 ships visual fidelity using mocks. Plan 26 erases the mocks one fetcher at a time.

---

## 2. Mock inventory (the work queue)

These are the files Plan 25 will create. This plan is "done" when each is deleted.

| Mock file | Surface | Backend plan that owns the endpoints | Contract track |
|---|---|---|---|
| `web/portal/lib/mock/customer.ts` | Customer dashboard (home, bookings, track, garage, rewards, account) | [13](./13-customer-dashboard.md) | [21](./21-api-contracts-track3-customer-dashboard.md) |
| `web/portal/lib/mock/provider.ts` | Provider dashboard (KPIs, jobs, schedule, earnings, customers, reviews, services, supplies) | [11](./11-provider-dashboard.md) | [20](./20-api-contracts-track2-provider-dashboard.md) |
| `web/admin/lib/mock.ts` | Admin dashboard (ops, map, bookings, detailers, customers, finance, marketing, cities, reviews, support, settings) | [24](./24-auth-pages-and-admin-dashboard.md) §6 | — (admin contracts emitted as part of 24) |
| inline `useState` in `(auth)/signup/page.tsx` steps 3-5 | Customer signup (vehicle preview, address coverage, promo) | [24](./24-auth-pages-and-admin-dashboard.md) §2 C-1/C-2/C-3 | [19](./19-api-contracts-track1-marketing.md) (ZIP coverage) |
| inline `useState` in `(auth)/onboarding/detailer/*` | Provider signup (7 steps: KYC, Checkr, docs, Plaid, equipment) | [24](./24-auth-pages-and-admin-dashboard.md) §3 P-1…P-5 | — |

**Grep these every wave to discover the queue:**

```bash
# Find every TODO(plan-NN) marker — those are placeholder types
grep -rn "TODO(plan-" web/portal/lib web/admin/lib

# Find every mock import — those are the swap sites
grep -rn "from \"@/lib/mock" web/portal web/admin
```

When both queries return zero, the plan is complete.

---

## 3. Protocol — for ONE mock export

This is the section to copy when scoping any individual swap. The skill at [`~/.claude/skills/backend/mock_to_backend.md`](file://C:/Users/yampi/.claude/skills/backend/mock_to_backend.md) elaborates each step with code samples.

### Step 1 — Read the mock to derive the implicit contract

The mock is the source of truth for what the UI needs. Inspect:

- The TypeScript shape: every field name, type, optional/required.
- The `satisfies` clause: if it `satisfies Appointment[]`, the API type already exists in `@/lib/api/types.ts`. If the `satisfies` clause uses a `TODO(plan-NN)` placeholder type, you'll define the real one in this swap.
- Whether the mock is a single object (point lookup), an array (list — needs pagination decision), or a composite (multiple sub-resources — common on dashboard "home" screens).

### Step 2 — Check if a real endpoint already exists

```bash
# Search the backend router aggregator and the OpenAPI catalogue
grep -rn "{resource}" backend/domains/*/router.py
grep -rn "{resource}" docs/api.md
```

| Outcome | Action |
|---|---|
| Endpoint exists and shape matches | Skip to Step 6 (wire fetcher). |
| Endpoint exists but shape doesn't match | Stop. Decide: (a) extend backend with new fields, (b) transform shape in fetcher (only if non-trivial computation is avoided). Default to (a) — never let the FE shape pollute the backend contract. |
| Endpoint doesn't exist | Continue to Step 3. |

### Step 3 — ARCHITECTURE validation (per execution_protocol §A)

Answer these before any code:

- Which domain owns this resource? (`backend/domains/{appointments,users,providers,vehicles,reviews,payments,...}`)
- Does it cross domain boundaries? If yes, the orchestration goes through a service in the *owning* domain — never a cross-import.
- Does the response need data from multiple domains? If yes, the route file aggregates (e.g. `domains/users/router.py` calls both `UserRepository` and `AppointmentRepository`); the new aggregator service lives in the owning domain.
- Does any failure mode (DB down, Stripe down, worker crash, WS drop) need a defined behavior? If not yet defined in `failure_modes` skill, STOP and define.

### Step 4 — CONTRACTS (Pydantic schemas FIRST)

Define `Envelope[T]` / `PaginatedEnvelope[T]` request and response schemas in `domains/{X}/schemas.py` *before* any router/service/repo code. Hard rules:

- Every new `/api/v1/*` endpoint MUST return `response_model=Envelope[T]` or `response_model=PaginatedEnvelope[T]` (see [`backend/shared/schemas.py`](../../backend/shared/schemas.py)). `EnvelopeRouter` raises at boot for any non-compliant route; CI test `test_envelope_compliance.py` enforces this.
- Prices are **integer cents** (`PositiveCents = int`). Never floats. The FE divides by 100 for display.
- Timestamps are UTC ISO-8601. The FE converts to local for display.
- For lists: cursor pagination via `Meta.cursor` / `prev_cursor` / `has_more` / `limit`. **Never** offset-based — it breaks under writes.
- Soft-deleted records (`is_deleted=true`) MUST be excluded from every default query. Pass an explicit `include_deleted=True` only inside admin-scoped paths.
- For audience-aware endpoints, document which roles can call it via `Depends(require_role(...))`.

After schemas land, update [`docs/api.md`](../api.md) with the new endpoint — same row format as the existing entries.

### Step 5 — IMPLEMENTATION (repository → service → router)

Strict order to avoid skill-loading regressions. Reference: [`backend-repository-pattern`](file://C:/Users/yampi/.claude/skills/backend/repository_pattern.md), [`backend-service-layer`](file://C:/Users/yampi/.claude/skills/backend/service_layer.md), [`backend-api-design`](file://C:/Users/yampi/.claude/skills/backend/api_design.md).

1. **Repository** (`domains/{X}/repository.py`): adds method(s). Async SQLAlchemy 2.0 (`select()`, `await session.execute()`). NEVER legacy `query()`. Always filter `is_deleted=False` unless the call signature explicitly accepts `include_deleted`. Returns ORM models or typed `Row` results — never dicts.
2. **Service** (`domains/{X}/service.py`): business logic only. No SQL. No HTTP calls. No direct cross-service calls (cross-domain orchestration goes through the *owning* domain's service, called from the router). Transaction-safe (`async with session.begin():` when mutating).
3. **Router** (`domains/{X}/router.py`): thin. Composes service + auth dep + Pydantic `response_model`. Returns `Envelope[T].model_validate(result)` or `PaginatedEnvelope[T]`.
4. **Aggregation** (`api/router.py`): include the new router only if it's a brand-new domain. For existing domains, the router is already aggregated.
5. **Idempotency**: if this endpoint mutates state and the FE may retry, decorate with the `Idempotency-Key` middleware (Redis-backed). Required for any payment-adjacent route.

### Step 6 — Frontend fetcher + hook

Portal pattern (`web/portal/`):

```ts
// web/portal/lib/api/customer.ts  — new
import { apiClient } from "@/lib/api/client";
import type { CustomerHome } from "@/lib/api/types";

export async function getCustomerHome(): Promise<CustomerHome> {
  const res = await apiClient.get("/customer/home");
  return res.data.data;  // unwrap Envelope[T]
}
```

```ts
// web/portal/lib/hooks/useCustomerHome.ts  — new
import useSWR from "swr";
import { getCustomerHome } from "@/lib/api/customer";

export function useCustomerHome() {
  return useSWR("customer-home", getCustomerHome);
}
```

Admin pattern (`web/admin/`) — uses raw fetch via `lib/api.ts`:

```ts
// web/admin/lib/api.ts  — extend existing
export async function getAdminOps() {
  return fetchEnvelope<AdminOps>("/admin/ops");
}
```

Both: define the real type in `@/lib/api/types.ts` (portal) or `@/lib/types.ts` (admin), and **delete** the `TODO(plan-NN)` placeholder type that Plan 25 left.

### Step 7 — Swap the import in the route

```diff
- import { MOCK_HOME } from "@/lib/mock/customer";
+ import { useCustomerHome } from "@/lib/hooks/useCustomerHome";
```

```diff
- export default function ClientHomePage() {
-   const data = MOCK_HOME;
+ "use client";
+ export default function ClientHomePage() {
+   const { data, isLoading, error } = useCustomerHome();
+   if (isLoading) return <PageSkeleton />;
+   if (error) return <ErrorState onRetry={...} />;
+   if (!data) return null;
```

Loading/error states are not optional. Use existing primitives — `PageSkeleton`, `EmptyState`, `ErrorBoundary`. Don't reinvent.

For server components, switch from `useX()` hook to a direct `await getX()` call and let the route's RSC machinery handle the loading shell via `loading.tsx`.

### Step 8 — VALIDATION

Required gates before merging:

- [ ] **Pytest**: a new test under `backend/tests/test_{domain}.py` covering happy path + 401 (unauthenticated) + 403 (wrong role, if applicable) + 404 (not found). Update the test-count table in [`AGENTS.md`](../../AGENTS.md) if a new test file is added.
- [ ] **Envelope compliance**: `test_envelope_compliance.py` still passes (it scans every `/api/v1/*` route at boot).
- [ ] **Type check (frontend)**: `cd web/portal && npx tsc --noEmit` and `cd web/admin && npx tsc --noEmit` both clean.
- [ ] **Audit log**: if this is a mutation, an `AuditRepository.log(...)` call lands inside the service. CI flags missing audit logs.
- [ ] **Observability**: `logger.info(...)` with `request_id` propagation on the entry/exit of the service method; structured JSON.
- [ ] **OpenAPI**: endpoint visible at `/docs` after restarting `uvicorn`. Response shows `Envelope[T]`.
- [ ] **Mock file shrinks**: the swapped `MOCK_X` export is deleted from `lib/mock/*.ts`. If the file is now empty, delete it.

### Step 9 — Update the trackers

After each swap:

1. Mark the corresponding row in [`docs/html-design-analysis.md`](../html-design-analysis.md) as "✅ wired" with the route link.
2. Tick the matching backend gap in the per-surface plan (11/13/24) under §"Backend gaps".
3. If a `TODO(plan-NN)` placeholder type was promoted to a real type, remove the marker.

---

## 4. Wave breakdown

Sized to land independent PRs. Each wave is ONE surface end-to-end. Run them in the same order Plan 25 ships the visual ports — that way the data session never blocks on a missing mock seam, and never lands a fetcher whose UI route doesn't exist yet.

### Wave 1 — Auth swaps (matches Plan 25 Wave 2)

The auth endpoints are ~90% already shipped (Plan 24 Waves 1 reused existing `/auth/identify`+`/auth/verify`). Outstanding swaps:

| Mock site | Backend gap | Existing plan |
|---|---|---|
| `(auth)/signup` step 3 vehicle price preview | `GET /api/v1/vehicles/price-estimate?year=&make=&model=` | [24](./24-auth-pages-and-admin-dashboard.md) §2 C-1 — **shipped** (commit `aa3aa1e`); just wire the fetcher |
| `(auth)/signup` step 4 ZIP coverage check | `POST /api/v1/public/coverage/check` | [24](./24-auth-pages-and-admin-dashboard.md) §2 C-3 — **shipped** (commit `f4e0103`); wire fetcher |
| `(auth)/signup` step 5 promo code `NEW10` | `POST /api/v1/promo/redeem` + `promo_codes` table | [24](./24-auth-pages-and-admin-dashboard.md) §2 C-2 — **NOT shipped**; this wave implements C-2 |
| `(auth)/onboarding/detailer/*` 7 steps | KYC, Checkr, document upload, Plaid bank link, equipment | [24](./24-auth-pages-and-admin-dashboard.md) §3 P-1…P-5 — **shipped P-1/P-2/P-3** (Wave 1); P-4 (Plaid) + P-5 (equipment) outstanding |

**Exit criteria:** every auth route's inline `useState` for steps 3-7 is replaced with real fetchers; provider signup can submit through to Plaid + equipment with mock-but-typed responses if the external integrations aren't ready (gate behind `NEXT_PUBLIC_FEATURE_PROVIDER_KYC_FULL`).

### Wave 2 — Customer Dashboard swaps (matches Plan 25 Wave 3)

Reads `web/portal/lib/mock/customer.ts` row by row. Owns plan 13 implementation. Per the existing plan:

- `useCustomerHome()` composite — backend gap (`GET /api/v1/clients/me/home` aggregating next appointment + KPIs + most-used vehicle).
- `useAppointments(filter)` — exists; just swap.
- `useAppointment(id)` for the track view — exists; just swap. Track view's live position uses the existing `WS /ws/appointments/{id}` (already implemented; per AGENTS.md).
- `useVehicles()` — exists; just swap.
- `useRewards()`, `useSubscriptions()`, `useFavorites()` — **all new domains** (loyalty, subscriptions, favorites). See Plan 13 for the model + endpoint design.
- `useReceipt(id)` — Plan 21 already has the contract; implementation lands here.

**Exit criteria:** `lib/mock/customer.ts` is deleted; six client routes render with live data + skeleton/error states; new domains `loyalty/`, `subscriptions/`, `favorites/` are wired.

### Wave 3 — Provider Dashboard swaps (matches Plan 25 Wave 4)

The largest wave. Reads `web/portal/lib/mock/provider.ts`. Owns plan 11 implementation. The big-ticket items:

- `useProviderKPIs()` composite — backend gap; involves cross-domain aggregation (appointments + reviews + payments). Aggregator lives in `domains/providers/service.py`, called from a new `providers_dashboard_router.py`.
- `useJobOffers()` + `acceptJob()` / `declineJob()` — backend gap; needs new `job_offers` table or extension of the existing matching system. Plan 11 §6 has the design.
- `useEarningsSeries(days)` — backend gap; daily rollup with `actual_price_cents - platform_fee`.
- `useSchedule(weekStart)` — exists partially via the availability endpoints; extend if needed.
- `useCustomerCRM()` — backend gap; lists every client who has booked this provider with rollups.
- `useServiceCatalog()` + `upsertService()` + `upsertAddon()` + `setAvailability()` — Plan 9 + Plan 11; extended schemas.
- `useReviews()` for the provider — exists via `domains/reviews/`; just swap.
- `useSupplies()` — Plan 11 §8; new domain `supplies/` if going through with the inventory tracking; otherwise defer with a `TODO(plan-11b)` flag.

**Exit criteria:** `lib/mock/provider.ts` is deleted; provider dashboard 12 views are live; `WS /ws/jobs/{provider_id}` (or pull-based with SWR refresh) emits new job offers; the "online/offline" toggle hits a real `PATCH /api/v1/providers/me/availability` endpoint.

### Wave 4 — Admin Dashboard swaps (matches Plan 25 Wave 5)

Reads `web/admin/lib/mock.ts`. Owns plan 24's admin §6.

- `getAdminOps()` composite — **W2-A shipped** (`GET /api/v1/admin/ops/dashboard?window=&city=` — KPIs + heatmap + cities rollup). FE swap: replace `MOCK_OPS` in `web/admin/lib/mock.ts` with `getAdminOps(window, city)`; promote the `delta`/`spark` fields when the V2 prior-period query lands.
- `getAdminBookings(filters)` — exists; extend filters.
- `getAdminDetailers(filters)` + verification actions — list/verification endpoints exist; **W2-C shipped** for the FSM actions (`POST /api/v1/admin/detailers/{id}/approve` and `/suspend` — operates on `application_status`; `suspended` is reversible via `/approve`). FE swap: drop the optimistic mock in `web/admin/lib/mock.ts` and call the real endpoints from the detailer detail drawer; render the new `previous_status` and `rejection_reason` fields in the timeline.
- `getAdminCustomers(filters)` — backend gap; admin-scoped users list.
- `getAdminFinance(range)` — backend gap; finance domain or finance-aggregator inside `domains/payments/`.
- `getAdminMarketing()` — Plan 15 (marketing CMS) — implement minimally here and let Plan 15 deepen.
- `getAdminCities()` — Plan 16 (coverage zips) drives this.
- `getAdminReviews()` — exists via `domains/reviews/`; just swap with admin filters.
- `getAdminSupport()` — backend gap; new domain `support/` or surfaces from audit log + a `tickets` table. Plan 24 has the broad shape.
- `getAdminSettings()` — admin-config endpoints (feature flags, platform fee schedule); Plan 24 + Plan 11's "fee schedule" gap.

**Exit criteria:** `web/admin/lib/mock.ts` is deleted; every dashboard route at `/dashboard/*` hits a real `/api/v1/admin/*` endpoint; admin role guard (`role=admin` Bearer) enforced everywhere; audit log captures every admin mutation (already required by `BaseService`).

### Wave 5 — Cleanup & verification

After Waves 1-4, run:

```bash
grep -rn "TODO(plan-" web/portal/lib web/admin/lib   # must be empty
grep -rn "from \"@/lib/mock" web/portal web/admin    # must be empty
ls web/portal/lib/mock/                              # must be empty or absent
ls web/admin/lib/mock.ts                             # must be absent
```

If all four queries are clean, this plan is **done**.

---

## 5. Hand-off contract with the frontend port session

Plan 25 keeps the frontend renderable through every wave of this plan. Discipline:

| Plan 25 (you ported) | Plan 26 (you swap) | Shared seam |
|---|---|---|
| Adds `MOCK_X` to `lib/mock/*.ts` with `satisfies SomeType` (real or `TODO(plan-NN)`) | Replaces `MOCK_X` consumers with real fetchers, deletes the export | The `lib/mock/*.ts` filename + named exports |
| `TODO(plan-NN)` placeholder type in `lib/api/types.ts` | Promotes to real type matching backend response | The type name (kept stable across the swap) |
| Loading/error UI not yet exercised | Wires `useSWR` `isLoading` / `error` to existing `PageSkeleton` / `ErrorState` | `components/app/{PageSkeleton,ErrorState}.tsx` |
| Routes are server components when possible | Same constraint — RSC stays server; client wrappers only for interactive leaves | RSC boundary in `page.tsx` |

**Coordination rule:** Wave N of Plan 26 ONLY starts after Wave N of Plan 25 lands. Both plans use the same wave numbering for this reason (Wave 2 in both = auth; Wave 3 = customer; Wave 4 = provider; Wave 5 = admin).

---

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Backend contract drifts from what the mock implies | Mock derives shape from the *real* type (via `satisfies`). If shape needs to differ, the swap explicitly upgrades the type — not the mock. |
| New domain (loyalty, subscriptions, supplies, support) takes too long to land | Each new domain is one PR. If it slips, defer the matching mock swap to a follow-up wave; the route still renders via mock. |
| Cross-domain aggregator endpoints (composite "home" responses) become slow | Composite endpoints MUST use cursor pagination on any embedded list. Profile in CI via `domains/admin/test_admin_ops_dashboard.py` pattern — assert <200 ms wall clock on the integration test. |
| Wave 3 (provider) leaks into Wave 4 (admin) because both touch payments | Two separate PRs; both call into the same `PaymentsRepository` — that repo is the shared component, not the route. Lock the repo's interface before either wave starts. |
| Idempotency-Key collisions when the FE retries a mutation | Every payment-adjacent mutation MUST use the Idempotency-Key middleware. Tests under `test_idempotency_*` already cover the boundary; add a case for any new mutation endpoint. |
| The data session needs a field the FE never asked for (e.g. server-side timestamps) | OK to add `meta` fields beyond what the mock encoded — the FE's `satisfies` clause already covers required fields only. The FE port adds new fields opportunistically when wiring. |
| Auth role guards mis-applied on admin endpoints | Every `/api/v1/admin/*` route uses `Depends(require_role("admin"))` — no exceptions. `test_admin.py` (27/27 today) already validates the boundary; add cases for any new admin endpoint. |

---

## 7. What "done" looks like

- [ ] Wave 1 merged: customer signup steps 3-5 and provider signup steps wired to real endpoints (or behind a feature flag for P-4/P-5 if external integrations aren't ready)
- [ ] Wave 2 merged: `web/portal/lib/mock/customer.ts` is deleted; six client routes live
- [ ] Wave 3 merged: `web/portal/lib/mock/provider.ts` is deleted; twelve provider routes live; `WS /ws/jobs/{provider_id}` (or equivalent) firing
- [ ] Wave 4 merged: `web/admin/lib/mock.ts` is deleted; eleven admin routes live; admin role guard everywhere
- [ ] Wave 5 merged: zero `TODO(plan-` markers; zero `from "@/lib/mock` imports; mock directories absent
- [ ] Test-count table in [`AGENTS.md`](../../AGENTS.md) updated with every new `test_{domain}.py` file
- [ ] `docs/api.md` updated with every new endpoint
- [ ] [`docs/html-design-analysis.md`](../html-design-analysis.md) every row marked "✅ wired" with route link

---

## 8. References

- The visual port plan this mirrors: [`25-designer-to-next-frontend.md`](./25-designer-to-next-frontend.md)
- Backend per-surface plans: [11](./11-provider-dashboard.md), [13](./13-customer-dashboard.md), [14](./14-mechanic-vertical.md), [24](./24-auth-pages-and-admin-dashboard.md)
- API contracts: [19](./19-api-contracts-track1-marketing.md), [20](./20-api-contracts-track2-provider-dashboard.md), [21](./21-api-contracts-track3-customer-dashboard.md)
- Mandatory pipeline: [`.claude/execution_protocol.md`](../../.claude/execution_protocol.md)
- Envelope contract: [`backend/shared/schemas.py`](../../backend/shared/schemas.py)
- Reusable protocol: [`~/.claude/skills/backend/mock_to_backend.md`](file://C:/Users/yampi/.claude/skills/backend/mock_to_backend.md)
