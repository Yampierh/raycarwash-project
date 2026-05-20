---
name: backend-mock-to-backend
description: Swap a frontend mock module (`lib/mock/*.ts`) for a real FastAPI endpoint + typed fetcher. Use whenever a UI route is rendering from hardcoded data and you need to land the backing API. Follows the project's mandatory ARCHITECTURE → CONTRACTS → DOMAIN SKILL → IMPLEMENTATION → OBSERVABILITY → VALIDATION pipeline.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - failure_modes
  - backend-api-design
  - backend-service-layer
  - backend-repository-pattern
preconditions:
  - The frontend mock exists at lib/mock/{surface}.ts with `satisfies` against a real or `TODO(plan-NN)`-flagged API type
  - The Envelope[T] / PaginatedEnvelope[T] conventions from backend/shared/schemas.py are understood
  - .claude/execution_protocol.md has been read once this session
outputs:
  - New repository methods + service methods + Pydantic schemas + router endpoint
  - New backend test file (or extended existing one)
  - New TS fetcher in lib/api/* + hook in lib/hooks/* (portal) or extension to lib/api.ts (admin)
  - Real type promoted in lib/api/types.ts (placeholder TODO(plan-NN) marker deleted)
  - Mock export deleted from lib/mock/*; mock file deleted when empty
conflicts:
  - Never bypass Envelope[T] / PaginatedEnvelope[T] on a /api/v1/* route
  - Never put SQL inside a service; never put business logic inside a repository
  - Never let the FE-imagined shape pollute the backend contract — fix the FE if it's wrong
  - Never delete a mock until the swap is type-clean + tested
execution_priority: 3
---

# Backend · Mock → Real Endpoint Protocol

**Use this when:** the frontend is rendering a screen from `lib/mock/X.ts` (typically created during a [[frontend-designer-to-next]] port) and the user asks to *wire it up* / *connect to real data* / *swap mocks*.

**Don't use this when:** you're designing a brand new endpoint with no UI driving the contract (use `backend-api-design` directly) or fixing a bug in an existing endpoint (use `ai-debugging`).

---

## 0. Mental model

The mock is the **demand-side contract**. The UI says: *"to render this screen, I need data shaped like this."* Your job is to make a real endpoint produce that shape under the project's architecture rules.

```
lib/mock/customer.ts                  →  Read this to learn what the UI wants.
       ↓ (this skill)
backend/domains/{X}/{schemas,        →  Implement following the mandatory pipeline.
                    repository,
                    service,
                    router}.py
       ↓
backend/tests/test_{X}.py            →  Lock the contract with tests.
       ↓
web/portal/lib/api/{X}.ts            →  Type-safe fetcher.
web/portal/lib/hooks/use{X}.ts       →  Optional SWR hook.
       ↓
web/portal/app/.../page.tsx          →  `import { MOCK_X }` → `import { useX }`.
       ↓
lib/mock/customer.ts                 →  Delete MOCK_X. If file empty, delete file.
```

When all four steps clear cleanly, the swap is done.

---

## 1. Read the mock — derive the implicit contract (5 min)

Open `lib/mock/<surface>.ts` and inspect ONE export at a time. For each:

| Question | How to answer |
|---|---|
| What's the field-by-field shape? | Read the literal. Note required vs. optional via TS `?`. |
| Does a real type already back it? | Look at the `satisfies` clause. If it says `satisfies Appointment[]`, the real type exists in `@/lib/api/types.ts`. If it says `satisfies Reward[] /* TODO(plan-13) */`, you'll define the real `Reward` type in this swap. |
| Is it a point lookup, a list, or a composite? | Object literal = point lookup. Array = list (needs pagination decision). Mixed object with embedded arrays = composite (common for dashboard "home" screens — aggregate endpoint). |
| Are there computed fields (deltas, percentages)? | They live server-side. The FE should receive precomputed numbers, not raw inputs. Example: `kpis.todayJobs.delta_pct` lands as a number, not as `(today / yesterday - 1)`. |
| Are prices floats or cents? | The backend ALWAYS uses **integer cents**. If the mock shows `price: 49.00`, fix the mock during the swap — it `satisfies` a wrong shape. The real type uses `price_cents: number`. |
| Are timestamps strings or Dates? | The wire format is ISO-8601 UTC strings. The FE parses to `Date` at render time. |

**Output of this step**: a one-paragraph contract description you can paste into the PR.

---

## 2. Check if the endpoint already exists (2 min)

```bash
# Search the routers
grep -rn "@router\." backend/domains/*/router.py | grep -i "{resource-name}"

# Check the API doc
grep -in "{resource-name}" docs/api.md

# Check the OpenAPI exposed by the running server (if dev is up)
curl -s http://localhost:8000/openapi.json | jq '.paths | keys[]' | grep {resource}
```

Three outcomes:

| Outcome | Action |
|---|---|
| Exists + shape matches mock | Skip to §7 (frontend wire). The work is just plumbing. |
| Exists + shape differs | Decide: extend backend (preferred — fix once) or transform in fetcher (only if the FE shape is *display-only* and trivial). Default is extend. |
| Doesn't exist | Continue to §3. |

---

## 3. ARCHITECTURE validation (per `.claude/execution_protocol.md` §A)

Before any code:

- **Which domain owns this resource?** Map to `backend/domains/{auth,admin,users,providers,vehicles,appointments,services_catalog,reviews,payments,matching,realtime,audit,notifications,public,locations}`. New conceptual entity → new domain. Existing entity → existing domain.
- **Does this cross domains?** A composite endpoint (e.g. customer "home" aggregates appointments + vehicles + reviews) is allowed, but the aggregator service must live in the *owning* domain (`domains/users/service.py` for a `customer_home` aggregator, since it's keyed off `current_user.id`). The aggregator calls *other domains' repositories* — never their services.
- **Failure modes covered?** What happens if DB times out? Stripe rejects? Worker crashes mid-mutation? WebSocket disconnects? Each must map to a defined behavior in the `failure_modes` skill. If not yet defined → STOP and add to that skill.
- **Soft delete invariant?** Every default query MUST filter `is_deleted = False`. Admin-scoped paths can pass `include_deleted=True` explicitly.
- **Boundary check**: does it violate `system_contracts`? Cross-domain import via `from domains.X.service import ...` (wrong) vs. `from domains.X.repository import ...` (allowed for read-only orchestration in router).

If any answer is "I don't know" → STOP, reload the relevant skill, retry.

---

## 4. CONTRACTS — Pydantic schemas FIRST

Define request + response schemas in `domains/{X}/schemas.py` *before* touching repository/service/router. Hard rules:

- Inherit from `_BaseSchema` (responses) or `_BaseRequestSchema` (requests). Both live in `backend/shared/schemas.py`. They set `from_attributes=True` and `str_strip_whitespace=True` consistently.
- Every `/api/v1/*` route returns `response_model=Envelope[T]` (single resource) or `response_model=PaginatedEnvelope[T]` (list). The `EnvelopeRouter` raises at boot if any route is non-compliant; CI test `test_envelope_compliance.py` enforces this.
- Prices: `int` cents (`PositiveCents = int`). Never floats.
- Timestamps: `datetime` (Pydantic emits ISO-8601 UTC). Stored as UTC in DB.
- Lists use cursor pagination via `Meta.cursor` / `prev_cursor` / `has_more` / `limit`. Never offset.
- Optional fields default to `None`; never use `Optional[X] = X(...)` unless the default is a sentinel (causes subtle Pydantic v2 bugs).

Template:

```python
# domains/X/schemas.py
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import Field
from shared.schemas import _BaseSchema, _BaseRequestSchema, PositiveCents


class RewardRead(_BaseSchema):
    id: UUID
    label: str
    points: int = Field(..., ge=0)
    tier: str  # "bronze" | "silver" | "gold"
    expires_at: datetime | None = None


class RewardRedeemRequest(_BaseRequestSchema):
    reward_id: UUID
```

Then update [`docs/api.md`](file:///c:/Users/yampi/Documents/Projects/raycarwash-project/docs/api.md) with the new endpoint row.

---

## 5. IMPLEMENTATION — strict order

Build the layers bottom-up. Each layer is independently testable.

### 5a. Repository (`domains/{X}/repository.py`)

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from domains.X.models import Reward


class RewardRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, user_id: UUID, *, include_deleted: bool = False) -> list[Reward]:
        stmt = select(Reward).where(Reward.user_id == user_id)
        if not include_deleted:
            stmt = stmt.where(Reward.is_deleted.is_(False))
        result = await self.db.execute(stmt.order_by(Reward.created_at.desc()))
        return result.scalars().all()
```

Hard rules:
- Async SQLAlchemy 2.0 (`select()`, `await session.execute()`). Never legacy `query()`.
- Always filter `is_deleted=False` unless the call signature accepts `include_deleted`.
- Returns ORM models or typed `Row` results — never dicts.
- No business logic. If you write `if reward.tier == "gold": ...` here, move it to the service.

### 5b. Service (`domains/{X}/service.py`)

```python
from domains.X.repository import RewardRepository


class RewardService:
    def __init__(self, repo: RewardRepository) -> None:
        self.repo = repo

    async def list_for_user(self, user_id: UUID) -> list[Reward]:
        return await self.repo.list_for_user(user_id)

    async def redeem(self, user_id: UUID, reward_id: UUID) -> Reward:
        reward = await self.repo.get(reward_id)
        if reward.user_id != user_id:
            raise PermissionError("Not your reward")
        if reward.is_expired:
            raise ValueError("Reward expired")
        async with self.repo.db.begin():
            redeemed = await self.repo.mark_redeemed(reward.id)
            await self._audit(user_id, redeemed)
        return redeemed
```

Hard rules:
- Business logic ONLY. No SQL. No HTTP calls. No direct cross-service calls (cross-domain orchestration goes through the *owning* domain via the router).
- Transaction-safe: any mutation runs inside `async with session.begin():`.
- Returns typed objects (not dicts).
- Audit log on every mutation: `AuditRepository(self.db).log(...)` inside the same transaction.

### 5c. Router (`domains/{X}/router.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.auth import get_current_user
from shared.schemas import Envelope, PaginatedEnvelope, Meta
from domains.X.schemas import RewardRead, RewardRedeemRequest
from domains.X.service import RewardService
from domains.X.repository import RewardRepository

router = APIRouter(tags=["Rewards"])


@router.get("/rewards", response_model=PaginatedEnvelope[RewardRead])
async def list_rewards(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
    limit: int = 20,
    cursor: str | None = None,
) -> PaginatedEnvelope[RewardRead]:
    service = RewardService(RewardRepository(db))
    items, next_cursor = await service.list_paginated(current_user.id, limit=limit, cursor=cursor)
    return PaginatedEnvelope[RewardRead](
        data=[RewardRead.model_validate(r) for r in items],
        meta=Meta(cursor=next_cursor, has_more=next_cursor is not None, limit=limit),
    )


@router.post(
    "/rewards/redeem",
    response_model=Envelope[RewardRead],
    status_code=status.HTTP_200_OK,
)
async def redeem_reward(
    payload: RewardRedeemRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
) -> Envelope[RewardRead]:
    service = RewardService(RewardRepository(db))
    try:
        redeemed = await service.redeem(current_user.id, payload.reward_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return Envelope[RewardRead](data=RewardRead.model_validate(redeemed))
```

Hard rules:
- Thin: composes service + auth dep + Pydantic. No DB calls. No business logic.
- Auth via `Depends(get_current_user)` or `Depends(require_role("admin"))`. Never skip auth on `/api/v1/*` unless the path is under `/api/v1/public/*`.
- `response_model` on every endpoint. CI fails otherwise.
- Document failure codes via `responses={401: {"model": ErrorEnvelope}, 403: {...}, 409: {...}}`.
- Mutations on payment-adjacent paths: add the `Idempotency-Key` dependency.

### 5d. Aggregation (`api/router.py`)

Only if it's a new domain — add `api_router.include_router(rewards_router)`. For existing domains, the router is already included.

### 5e. Migrations (`backend/alembic/`)

If a new table or column is involved:

```bash
cd backend && alembic revision --autogenerate -m "add_rewards_table"
# Inspect the generated migration — autogenerate misses ENUMs and CHECK constraints
cd backend && alembic upgrade head
```

Migration hygiene:
- Add explicit `op.create_index(...)` for any column you'll filter or sort on.
- Soft-delete columns: `is_deleted BOOLEAN NOT NULL DEFAULT FALSE` + `deleted_at TIMESTAMPTZ NULL` (matches the project standard).
- Encrypted PII: use `EncryptedType` from the existing pattern; don't reinvent.

---

## 6. VALIDATION — tests + observability + audit

### 6a. Tests

Create `backend/tests/test_{X}.py` (or extend existing) covering:

- ✅ Happy path: authenticated user, valid input → `Envelope` shaped response with expected fields.
- ✅ 401: no Bearer token → `ErrorEnvelope` with `code=authentication_required`.
- ✅ 403: wrong role / wrong user → `ErrorEnvelope` with `code=permission_denied`.
- ✅ 404: resource doesn't exist → `ErrorEnvelope` with `code=resource_not_found`.
- ✅ 409: state conflict (already redeemed, expired, etc.) → `ErrorEnvelope` with `code=conflict`.
- ✅ Soft-delete invariant: deleted record doesn't appear in list.
- ✅ For mutations: audit log row exists after the call.

Pattern (from `backend/tests/test_appointments.py`):

```python
@pytest.mark.asyncio
async def test_list_rewards_returns_envelope(client, authed_user):
    resp = await client.get("/api/v1/rewards", headers=authed_user.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body and "meta" in body
    assert isinstance(body["data"], list)
    assert body["meta"]["has_more"] in (True, False)


@pytest.mark.asyncio
async def test_redeem_reward_404_when_not_owned(client, authed_user, other_users_reward):
    resp = await client.post(
        "/api/v1/rewards/redeem",
        json={"reward_id": str(other_users_reward.id)},
        headers=authed_user.headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "permission_denied"
```

Run `pytest backend/tests/test_{X}.py -q` until green. Update the test-count table in [`AGENTS.md`](file:///c:/Users/yampi/Documents/Projects/raycarwash-project/AGENTS.md).

### 6b. Observability

Every service method gets a `logger.info(...)` at entry + a structured log at exit:

```python
import structlog
logger = structlog.get_logger(__name__)

async def redeem(self, user_id: UUID, reward_id: UUID) -> Reward:
    log = logger.bind(user_id=str(user_id), reward_id=str(reward_id))
    log.info("reward.redeem.start")
    # ... work ...
    log.info("reward.redeem.done", points=redeemed.points)
    return redeemed
```

`request_id` is propagated automatically by the middleware stack (RequestID → StructuredLogging → AuditContext → Idempotency).

### 6c. Audit

Every mutation appends to `domains/audit`:

```python
from domains.audit.repository import AuditRepository
from domains.audit.models import AuditAction

await AuditRepository(self.db).log(
    action=AuditAction.REWARD_REDEEMED,
    entity_type="reward",
    entity_id=str(redeemed.id),
    actor_id=user_id,
    metadata={"points": redeemed.points, "tier": redeemed.tier},
)
```

CI catches missing audit logs on mutation endpoints.

---

## 7. FRONTEND — wire the typed fetcher

Two patterns depending on which app:

### 7a. Portal (`web/portal/`) — Axios + SWR

```ts
// web/portal/lib/api/rewards.ts  — NEW
import { apiClient } from "@/lib/api/client";  // injects access_token + handles refresh
import type { Reward } from "@/lib/api/types";

export async function getRewards(): Promise<Reward[]> {
  const res = await apiClient.get("/rewards");
  return res.data.data;  // unwrap Envelope[T].data → array
}

export async function redeemReward(reward_id: string): Promise<Reward> {
  const res = await apiClient.post("/rewards/redeem", { reward_id });
  return res.data.data;  // unwrap Envelope[T].data → object
}
```

```ts
// web/portal/lib/hooks/useRewards.ts  — NEW
import useSWR from "swr";
import { getRewards } from "@/lib/api/rewards";

export function useRewards() {
  return useSWR("rewards", getRewards);
}
```

```ts
// web/portal/lib/api/types.ts  — PROMOTE the placeholder
// BEFORE (left by Plan 25):
// export type Reward = { /* TODO(plan-13): real shape */ id: string; ... };
//
// AFTER (this swap):
export type Reward = {
  id: string;
  label: string;
  points: number;
  tier: "bronze" | "silver" | "gold";
  expires_at: string | null;  // ISO-8601 UTC
};
```

**Critical:** the TS type must match the Pydantic `RewardRead` field-for-field. If they drift, the frontend's `satisfies` clause fails and the type-check breaks.

### 7b. Admin (`web/admin/`) — raw fetch

```ts
// web/admin/lib/api.ts  — EXTEND
import type { AdminOps } from "./types";

export async function getAdminOps(): Promise<AdminOps> {
  return fetchEnvelope<AdminOps>("/admin/ops");  // existing helper
}
```

Admin has no i18n and no SWR by default — most pages do `useEffect(() => { fetchX().then(setX) }, [])`. Don't refactor that pattern during a swap; match what the route already does.

---

## 8. Swap the import + handle states

```diff
# web/portal/app/[locale]/(app)/client/rewards/page.tsx
-import { MOCK_REWARDS } from "@/lib/mock/customer";
+"use client";
+import { useRewards } from "@/lib/hooks/useRewards";
+import { PageSkeleton } from "@/components/app/PageSkeleton";
+import { ErrorState } from "@/components/app/ErrorState";

-export default function RewardsPage() {
-  const rewards = MOCK_REWARDS;
+export default function RewardsPage() {
+  const { data: rewards, isLoading, error, mutate } = useRewards();
+  if (isLoading) return <PageSkeleton />;
+  if (error) return <ErrorState onRetry={() => mutate()} />;
+  if (!rewards) return null;
```

Loading + error states are not optional. Use the project's existing primitives — don't reinvent.

For **server components** (no `useState`/`useEffect`/`onClick`), swap differently:

```diff
-import { MOCK_REWARDS } from "@/lib/mock/customer";
+import { getRewards } from "@/lib/api/rewards";

-export default function RewardsPage() {
-  const rewards = MOCK_REWARDS;
+export default async function RewardsPage() {
+  const rewards = await getRewards();
```

Loading state goes in `app/.../rewards/loading.tsx`. Error in `error.tsx`. Both are Next.js conventions.

---

## 9. Delete the mock

After the swap compiles + renders + tests pass:

```diff
// web/portal/lib/mock/customer.ts
-export const MOCK_REWARDS: Reward[] = [
-  { id: "r1", label: "Free interior wash", points: 500, tier: "bronze", expires_at: null },
-  // ...
-];
```

If the file is now empty (no remaining exports), delete it entirely (`rm web/portal/lib/mock/customer.ts`). Update any barrel `lib/mock/index.ts` re-export.

Sanity grep:

```bash
grep -rn "MOCK_REWARDS\|from \"@/lib/mock/customer\"" web/portal
# Expected: zero results
```

---

## 10. Update the trackers

1. [`docs/html-design-analysis.md`](file:///c:/Users/yampi/Documents/Projects/raycarwash-project/docs/html-design-analysis.md): mark the row "✅ wired" with the route link.
2. The per-surface plan (e.g. `13-customer-dashboard.md`): tick the backend gap.
3. If a `TODO(plan-NN)` placeholder type was promoted, remove the marker.
4. If a new test file was added, update [`AGENTS.md`](file:///c:/Users/yampi/Documents/Projects/raycarwash-project/AGENTS.md) test-count table.
5. [`docs/api.md`](file:///c:/Users/yampi/Documents/Projects/raycarwash-project/docs/api.md): add the new endpoint row.

---

## 11. Output validation checklist (per `.claude/execution_protocol.md` §5)

Before opening the PR:

- [ ] No SQL in services (`grep -n "select(" backend/domains/X/service.py` → empty)
- [ ] No business logic in repositories (`grep -nE "if .+\..+ == |raise (ValueError|PermissionError)" backend/domains/X/repository.py` → empty)
- [ ] No schema-less endpoints (every `@router.X` has `response_model=`)
- [ ] No missing audit logs on mutations (every `async with session.begin():` has a sibling `AuditRepository.log(...)`)
- [ ] No bypassed state machine rules (e.g. appointment FSM transitions go through `appointment_state_machine`)
- [ ] No cross-domain imports violating boundaries (`from domains.X.service` only inside `domains/X/`)
- [ ] All async operations awaited (`grep -n "session.execute(" backend/domains/X/` → all preceded by `await`)
- [ ] All DB mutations transactional (`async with session.begin():`)
- [ ] Envelope compliance test still green
- [ ] OpenAPI shows the new route at `/docs`
- [ ] FE type-check (`cd web/portal && npx tsc --noEmit`) clean
- [ ] Mock export deleted (grep returns zero)

---

## 12. Things to never do

- ❌ Return a raw dict from a router (`return {"id": str(x.id)}` — must be `Envelope[T](data=...).model_validate()`).
- ❌ Put `select()` inside a service.
- ❌ Put `if reward.tier == "gold": ...` inside a repository.
- ❌ Float prices. Cents everywhere.
- ❌ Skip the audit log on a mutation.
- ❌ Add a new `/api/v1/*` route without `response_model=`.
- ❌ Delete a mock before the swap is type-clean AND tested.
- ❌ Make the backend match a wrong FE shape — fix the FE type instead.
- ❌ Bypass the Idempotency-Key middleware on payment-adjacent mutations.
- ❌ Loop SWR refresh in a `useEffect` to "force" updates — use `mutate()` instead.
- ❌ Cross-domain imports of `service.py` (only `repository.py` is allowed for read-only orchestration).
- ❌ Add `Optional[X] = X(...)` Pydantic defaults — known v2 footgun, use `X | None = None`.

---

## 13. Pitfalls noted in practice

| Symptom | Cause | Fix |
|---|---|---|
| `TypeError: Object of type UUID is not JSON serializable` | Pydantic v2 needs explicit UUID serialization in some envelope paths | Either `id: str` in the schema (and stringify in the service) or use `model_dump(mode="json")` |
| FE shows stale data after a mutation | SWR cache not invalidated | Call `mutate("key")` from the global SWR config, or pass `mutate` from the hook and call it after the mutation |
| Endpoint returns 200 but FE shows `undefined` | Forgot to unwrap `Envelope[T]` — fetcher returned `res.data` instead of `res.data.data` | Always unwrap one level: `Envelope.data` is the actual payload |
| Tests pass locally but `test_envelope_compliance.py` fails in CI | Route registered before its schema was decorated; or `response_model=` missing | Restart the test runner — `EnvelopeRouter` validates at boot, and the dev process can cache stale state |
| Cross-user data leak | Repository method didn't filter by `user_id` | Always make `user_id` a required parameter in repo methods; never trust `current_user` to be passed implicitly |
| Soft-deleted record reappears | Missing `is_deleted=False` filter on a new query | Default to filtering; add `include_deleted` only as an explicit override flag |
| Pagination cursor doesn't advance | Returning the cursor from the wrong row (e.g. first instead of last) | The cursor is the LAST row's stable ordering key. Use `created_at` (or PK) descending, last item's value becomes the next cursor |
| WebSocket clients don't receive updates | Mutation didn't notify the realtime worker | Inside the service, after the transaction commits, call `realtime.publish(...)` — or rely on the `notifications/handlers.py` event subscribers |
| Heatmap / hour-of-day aggregate buckets wrong in dev vs CI | `extract(hour, ts)` on a `timestamp with time zone` column uses the Postgres SESSION TZ, which is EDT in dev (Windows + local install) and UTC in CI / prod. A 12:00 UTC appointment lands in the 08:00 bucket in dev. | Cast to UTC explicitly in the query: `func.timezone("UTC", Appointment.scheduled_time)` then extract from that. Document the V1 trade-off ("UTC bucketing; per-city tz refinement is later") in the schema docstring. |
| Admin endpoint fails `test_envelope_compliance` after a Wave 2 swap | The new admin endpoint was put on `EnvelopeRouter` but admin returns raw schemas by convention | Check `tests/test_envelope_compliance.py LEGACY_PATH_PREFIXES` — `/api/v1/admin/` is in the legacy allow-list. Keep new admin endpoints on plain `APIRouter` with raw `response_model=AdminFooSchema` to match the existing admin pattern. Migrating admin to envelope is a separate sweep. |
| Test pass for one endpoint but fail when run with the full suite | Conftest seeds RBAC + services + addons but NOT cities or other lookup tables. Tests that depend on city codes pass in isolation (cities seeded earlier in another test's bleed-over) but break with `conftest.py`'s drop-recreate cycle. | Each test that depends on the `cities` table calls `await seed_cities(db_session)` explicitly — see `tests/test_admin_ops_dashboard.py` and `tests/test_users_provider_profile.py` for the pattern. |

---

## 14. Aggregate / dashboard endpoint patterns

Dashboard endpoints (KPI tiles, heatmaps, city rollups, finance summaries) have repeating shapes. The W2-A `GET /admin/ops/dashboard` ship surfaced these patterns — apply them when porting `MOCK_*` exports that wrap a whole screen's worth of stats.

### 14a. KPI tile shape — reserve `delta` and `spark`

Designer dashboards almost always show KPI tiles with **value + delta vs prior period + sparkline**. Shipping all three in V1 is expensive (each tile needs a paired prior-period query + bucket series). Ship a scalar value first; reserve the other fields so the FE can render the tile shell without breaking when V2 fills them in.

```python
class OpsKpiValue(BaseModel):
    """A single KPI tile. `delta` and `spark` are reserved for future
    iterations — set to 0 / [] in V1 so the frontend can render the
    tile shell without breaking."""

    value: float
    delta: float = 0.0
    spark: list[float] = Field(default_factory=list)
```

V2 endpoint adds the paired prior-window query + bucketed series. No schema migration needed.

### 14b. Time bucketing — extract in UTC explicitly

`func.extract("hour", Appointment.scheduled_time)` uses the Postgres session TZ. In a multi-environment project (Windows dev = EDT, CI/prod = UTC) the same data lands in different buckets. Always cast to UTC first:

```python
utc_scheduled = func.timezone("UTC", Appointment.scheduled_time)
dow_expr  = func.extract("dow", utc_scheduled)
hour_expr = func.extract("hour", utc_scheduled)
```

Document the V1 trade-off in the schema docstring: *"Uses UTC; per-city timezone bucketing is a Wave 4 refinement."* When per-city TZ matters (Indianapolis EST/EDT vs Louisville etc.), join on `cities.timezone` and `AT TIME ZONE city.timezone` instead. Don't carry this complexity in V1.

### 14c. Per-group rollups — N small grouped queries, not one mega-join

When the FE needs the same dimension cut multiple ways (e.g. *per-city*: detailers, online detailers, in-flight jobs), prefer N small `GROUP BY` queries returning `dict[key, int]` over one giant join.

```python
per_city_detailers: dict[str, int] = {
    code: n
    for code, n in (await db.execute(
        select(ProviderProfile.home_city_code, func.count(ProviderProfile.id))
        .where(ProviderProfile.home_city_code.is_not(None),
               ProviderProfile.application_status == "approved")
        .group_by(ProviderProfile.home_city_code)
    )).all()
}

# Stitch rollups in Python at the end:
rows = [
    OpsCityRow(
        code=c.code,
        name=c.name,
        detailers=per_city_detailers.get(c.code, 0),
        online=per_city_online.get(c.code, 0),
        jobs=per_city_jobs.get(c.code, 0),
    )
    for c in all_cities
]
```

Why: each grouped query reads one index, returns a small dict, and is easy to test in isolation. The mega-join with `CASE WHEN ... THEN 1 END` columns is harder to read, harder to optimise, and breaks when one of the dimensions has zero rows.

### 14d. Window helper for time-window endpoints

When an endpoint accepts a Literal of period codes (`"1h" | "today" | "7d" | "30d" | "90d"`), a single resolver helper keeps the route + query logic clean:

```python
def _resolve_window(window: OpsWindow, now: datetime) -> tuple[datetime, datetime]:
    if window == "1h":    return now - timedelta(hours=1), now
    if window == "today": return now.replace(hour=0, minute=0, second=0, microsecond=0), now
    if window == "7d":    return now - timedelta(days=7), now
    if window == "30d":   return now - timedelta(days=30), now
    if window == "90d":   return now - timedelta(days=90), now
    raise ValueError(f"Unsupported window: {window}")
```

Pydantic `Literal` validation rejects bad values before the helper runs — the route file `get_args(OpsWindow)` check is a belt-and-suspenders for non-FastAPI callers.

### 14e. Proxy bucketing when the canonical FK is missing

Some entities don't yet have the FK that the dashboard wants to cut by. Example: `appointments` don't carry a `city_id` (V1 used the detailer's `home_city_code` as a proxy until a real city tag lands).

The rule: use the proxy, **document it in the repo method docstring**, and add a `TODO(plan-NN)` for the canonical column. Future-you doesn't have to re-derive the design decision.

```python
async def get_ops_dashboard(self, ..., city: str = "all") -> dict:
    """...

    Bookings are bucketed by the detailer's `home_city_code` as a
    proxy until appointments carry an explicit city tag (see Plan 24
    §5.3 — A-2). When `city != 'all'`, KPIs scope to that city."""
```

### 14f. Admin endpoints — don't force Envelope[T] retrofit

`/api/v1/admin/` is in `tests/test_envelope_compliance.py`'s `LEGACY_PATH_PREFIXES`. New admin endpoints should use plain `APIRouter` with raw `response_model=AdminFooSchema` to match the existing admin convention. The Envelope migration for admin is a separate, cross-cutting sweep — don't bundle it with a per-endpoint feature swap.

The FE pattern matches: `web/admin/lib/api.ts` `fetchEnvelope` and `fetchPlain` exist side-by-side; admin routes call the right one.

### 14g. Test setup for aggregate endpoints

When testing an aggregate endpoint that depends on lookup tables (cities, services, addons), check what `tests/conftest.py` seeds — and seed the rest yourself:

```python
from app.db.seed_cities import seed_cities

async def test_seeded_cities_appear_in_rollup(client, db_session):
    await seed_cities(db_session)
    headers = await _admin_headers(client, db_session)
    resp = await client.get("/api/v1/admin/ops/dashboard", headers=headers)
    ...
```

Aggregate tests also benefit from a window parameter sweep:

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("window", ["1h", "today", "7d", "30d", "90d"])
async def test_each_window_accepted(client, db_session, window):
    ...
```

— catches `_resolve_window` regressions cheaply.

---

## 15. Quick checklist (printable)

For each `MOCK_X` swap:

- [ ] Read mock → derive contract shape
- [ ] Confirm domain ownership + failure modes
- [ ] Define Pydantic schemas (Envelope/PaginatedEnvelope)
- [ ] Update `docs/api.md`
- [ ] Repository: async SQLAlchemy 2.0, soft-delete filter, typed return
- [ ] Service: business logic, transaction wrapper, audit log
- [ ] Router: thin, `response_model=`, auth dep, error codes
- [ ] Migration (if schema change)
- [ ] Test: happy + 401/403/404/409 + soft-delete invariant + audit row
- [ ] Observability: structured logs at service entry/exit
- [ ] FE fetcher (`lib/api/X.ts`) + optional hook (`lib/hooks/useX.ts`)
- [ ] Promote `TODO(plan-NN)` placeholder type to real type
- [ ] Swap import in route file
- [ ] Add loading + error states
- [ ] Delete mock export (and file if empty)
- [ ] Update `html-design-analysis.md` + plan tracker + `AGENTS.md` test count
- [ ] FE `tsc --noEmit` clean; backend `pytest` clean; envelope-compliance green

---

## 16. When to escalate

Stop and ask the user when:

- The mock's shape is fundamentally incompatible with the architecture (e.g. encodes a denormalized join that can't be efficiently served without breaking domain boundaries) → propose a different shape and confirm.
- A new domain is needed (loyalty, subscriptions, supplies, support) and the per-surface plan doesn't yet describe the model — confirm scope before scaffolding.
- The endpoint requires a third-party integration not yet in the project (Plaid for bank linking, Checkr for background checks) — confirm the integration plan and credentials before stubbing the call site.
- A mutation could create irreversible state (sending money, deleting user data, charging a card) → confirm idempotency design and audit semantics before implementing.
- The mock implies a real-time push (WebSocket) but the architecture has only pull-based polling — confirm whether to extend the realtime domain or fall back to SWR refresh-on-interval.
