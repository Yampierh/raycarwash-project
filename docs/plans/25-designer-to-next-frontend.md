# 25 — Designer → Next Frontend Integration

> **Status:** Planning
> **Priority:** High
> **Dependencies:** none on backend side (this plan is *frontend port only*); soft deps on **Plan 11** (provider dashboard data), **Plan 13** (customer dashboard data), **Plan 24** (auth pages + admin backend).
> **Out of scope:** wiring real data (a separate session owns mock→backend swap, tracked by Plans 11/13/24 + the contract tracks 19/20/21). This plan ships the **visual & structural fidelity** only — every screen reaches "Designer-parity" running on hardcoded data, ready for the data session to swap.
> **Design source:** [`raycarwash/project/`](../../raycarwash/project) — 12 HTML wrappers + ~60 JSX components + 8 CSS files (~17K LOC). Inventory at [`docs/html-design-analysis.md`](../html-design-analysis.md).
> **Skill:** [`~/.claude/skills/frontend/designer_to_next.md`](file://C:/Users/yampi/.claude/skills/frontend/designer_to_next.md) — codifies the protocol used here so future Designer drops follow the same flow.

---

## 1. Why this plan exists

Claude Designer ships pages as a browser bundle: one HTML wrapper per page that boots React 18 via UMD + `@babel/standalone`, fetches a hand-picked list of `.jsx` files, and applies a stack of `.css` files. The bundle is *high-fidelity but disposable* — it doesn't compile, has no TypeScript, leaks the `TweaksPanel` design tool, and ships duplicate UMD copies of React. Production lives in two Next.js 16 apps (`web/portal/` on :3001, `web/admin/` on :3000).

We have **already migrated** the marketing surfaces in Plan 12 (Phases 1-4 done). What remains is:

| Surface | State today | What this plan ships |
|---|---|---|
| **Auth pages** (5: customer login/signup, provider login/signup, staff login) | `web/portal/(auth)/login` is barebones, `signup` is barebones, no provider 7-step signup, no staff login surface | All 5 pages ported into `web/portal/(auth)/*` + `web/admin/login/` matching the designer pixel-for-pixel |
| **Customer Dashboard** | Only `client/home/page.tsx` exists as a stat-card stub | 6 views (`home`, `bookings`, `track`, `garage`, `rewards`, `account`) + shell |
| **Provider Dashboard** | `detailer/home`, `jobs`, `services`, `earnings`, `profile` exist as skeletons | 12 views + global shell (sidebar, notifications, online toggle, search, "new job" CTA) |
| **Admin Dashboard** | Dark zinc-950 page with 8 stat cards + 6 stub list routes | 11 designer views (Ops, Map, Bookings, Detailers, Customers, Finance, Marketing, Cities, Reviews, Support, Settings) + redesigned shell |

The work is **structural & visual only**. Every component lands with *hardcoded data from the JSX bundle's `dash-data.jsx` / `cdash-data.jsx` / `admin-data.jsx` translated into local TS modules*, behind a single import boundary (`lib/mock/*`) so the data session can swap module-by-module.

---

## 2. Source inventory (what to port)

Numbers below are exact line counts from `raycarwash/project/src/*.jsx`.

### 2.1 Auth (`auth.css` 493 LOC)

| HTML | JSX entry | JSX size | Destination |
|---|---|---|---|
| `Customer Login.html` | `customer-login.jsx` | 229 | `web/portal/app/[locale]/(auth)/login/page.tsx` (replace existing) |
| `Customer Signup.html` | `customer-signup.jsx` | 381 | `web/portal/app/[locale]/(auth)/signup/page.tsx` (replace existing) |
| `Provider Login.html` | `provider-login.jsx` | 196 | `web/portal/app/[locale]/(auth)/login/page.tsx` (audience-aware — same route, role toggle already wired) |
| `Provider Signup.html` | `provider-signup.jsx` | 635 | `web/portal/app/[locale]/(auth)/signup/role/detailer/page.tsx` + `(auth)/onboarding/detailer/*` (7-step wizard) |
| `Staff Login.html` | `staff-login.jsx` | 258 | `web/admin/app/login/page.tsx` (replace existing) |
| shared | `auth-bits.jsx` | 224 | `web/portal/components/auth/{TextField,PasswordField,OtpInput,StepProgress,SocialButtons}.tsx` + admin copies under `web/admin/components/auth/` |

### 2.2 Customer Dashboard (`cdash.css` 614 LOC + shared `dashboard.css` 1048 LOC)

| JSX | LOC | Destination |
|---|---|---|
| `cdash-shell.jsx` | 196 | `web/portal/components/app/CustomerShell.tsx` (sidebar + topbar + main slot) |
| `cdash-home.jsx` | 265 | `(app)/client/home/page.tsx` (replace stub) |
| `cdash-bookings.jsx` | 176 | `(app)/client/appointments/page.tsx` (replace stub) |
| `cdash-track.jsx` | 155 | `(app)/client/appointments/[id]/track/page.tsx` (new) |
| `cdash-garage.jsx` | 141 | `(app)/client/vehicles/page.tsx` (replace stub) |
| `cdash-rewards.jsx` | 168 | `(app)/client/rewards/page.tsx` (new) |
| `cdash-account.jsx` | 274 | `(app)/client/profile/page.tsx` (replace stub) |
| `cdash-icons.jsx` | 46 | `web/portal/components/icons/customer.tsx` *(only icons not in `lucide-react`)* |
| `cdash-data.jsx` | 140 | `web/portal/lib/mock/customer.ts` |

### 2.3 Provider Dashboard (`dashboard.css` 1048 LOC)

| JSX | LOC | Destination |
|---|---|---|
| `dash-shell.jsx` | 219 | `web/portal/components/app/ProviderShell.tsx` |
| `dash-overview.jsx` | 356 | `(app)/detailer/home/page.tsx` (replace stub) |
| `dash-jobs.jsx` | 275 | `(app)/detailer/jobs/page.tsx` (replace stub) |
| `dash-schedule.jsx` | 145 | `(app)/detailer/schedule/page.tsx` (new) |
| `dash-earnings.jsx` | 223 | `(app)/detailer/earnings/page.tsx` (replace stub) |
| `dash-customers.jsx` | 140 | `(app)/detailer/customers/page.tsx` (new) |
| `dash-reviews.jsx` | 155 | `(app)/detailer/reviews/page.tsx` (new) |
| `dash-services.jsx` | 493 | `(app)/detailer/services/page.tsx` (replace stub) — has 5 sub-views (catalog / addons / pricing / availability / settings) — keep as one route with tabs to match the Designer layout |
| `dash-icons.jsx` | 113 | `web/portal/components/icons/provider.tsx` |
| `dash-data.jsx` | 197 | `web/portal/lib/mock/provider.ts` |

### 2.4 Admin Dashboard (`admin.css` 919 LOC + shared `dashboard.css`)

| JSX | LOC | Destination |
|---|---|---|
| `admin-shell.jsx` | 96 | `web/admin/components/Shell.tsx` (replace stub `sidebar.tsx`) |
| `admin-header.jsx` | 92 | `web/admin/components/Header.tsx` |
| `admin-ops.jsx` | 203 | `web/admin/app/dashboard/page.tsx` (replace overview stub) |
| `admin-map.jsx` | 126 | `web/admin/app/dashboard/map/page.tsx` (new) |
| `admin-bookings.jsx` | 162 | `web/admin/app/dashboard/appointments/page.tsx` (replace stub) |
| `admin-detailers.jsx` | 115 | `web/admin/app/dashboard/detailers/page.tsx` (new) |
| `admin-customers.jsx` | 101 | `web/admin/app/dashboard/customers/page.tsx` (new) |
| `admin-finance.jsx` | 151 | `web/admin/app/dashboard/finance/page.tsx` (new) |
| `admin-marketing.jsx` | 124 | `web/admin/app/dashboard/marketing/page.tsx` (new) |
| `admin-cities.jsx` | 142 | `web/admin/app/dashboard/cities/page.tsx` (new) |
| `admin-reviews.jsx` | 111 | `web/admin/app/dashboard/reviews/page.tsx` (new) |
| `admin-support.jsx` | 89 | `web/admin/app/dashboard/support/page.tsx` (new) |
| `admin-settings.jsx` | 127 | `web/admin/app/dashboard/settings/page.tsx` (new) |
| `admin-bits.jsx` | 104 | `web/admin/components/Bits.tsx` (Card / Pill / Stat / SortHeader / Drawer) |
| `admin-icons.jsx` | 41 | `web/admin/components/icons.tsx` |
| `admin-data.jsx` | 203 | `web/admin/lib/mock.ts` |

### 2.5 Things we deliberately drop

| Designer artifact | Why it doesn't ship |
|---|---|
| `tweaks-panel.jsx` (568 LOC) | Design-time control surface — brand color / density / audience toggle. Not for prod. Audience toggle survives separately via `useAudienceStore` (Plan 12). |
| `EDITMODE-BEGIN`/`EDITMODE-END` markers and `useTweaks` hook | Designer-only persistence layer (LocalStorage key `__rcw_tweaks`) — replaced by `useAudienceStore` + Tailwind theme tokens. |
| Per-page HTML bootstrap shells | Replaced by Next.js routing; HTMLs are reference, not shipped. |
| UMD React + Babel-standalone scripts | Replaced by Next.js build pipeline. |
| `?t=...` cache-bust query | Irrelevant under Next's hashed asset pipeline. |

---

## 3. Conventions (the protocol)

Every screen ported under this plan follows the same six steps. These are also the steps codified in the skill at `~/.claude/skills/frontend/designer_to_next.md`.

### Step 1 — Pin the design tokens (one-time, already done)

Tokens already live in [`web/portal/app/globals.css`](../../web/portal/app/globals.css) (Plan 12 §0). For `web/admin/`, mirror the same `@theme` block (Tailwind v4) but keep the existing `bg-zinc-950` dark surfaces. Add the missing JetBrains Mono font (used by admin) via `next/font/google`. **Never** introduce a per-page color literal — always reference `brand-*` / `ink-*` tokens.

### Step 2 — Split each JSX file into RSC-compatible components

Designer JSX is one big `function` per concern with `React.useState` at top. The port rule:

1. The route file (`page.tsx`) is **server** unless the entire screen is interactive. Use `(app)/client/home/page.tsx` (Plan 12) as the reference shape.
2. Interactive widgets (accordions, tabs, sliders, calendar pickers, charts, drawer panels) become `"use client"` leaf components under `components/app/` (portal) or `components/` (admin).
3. Lists/tables that mutate via filters become client components; the route stays server and passes the seed data prop.
4. Use existing primitives — **never re-create them**:
   - `components/forms/{Button,Input,Select,Checkbox,FormError}.tsx` (portal)
   - `components/app/{PageHeader,AppShell,EmptyState,AppointmentStatusBadge,VehicleForm,CheckoutForm}.tsx` (portal)
   - `Bits.tsx` for the admin equivalent (must be created in Wave 4)
   - Icons: `lucide-react` for anything that has a match. Only port a designer icon to `components/icons/*.tsx` when `lucide-react` lacks an exact equivalent (rare — phone-mock screens, custom logo glyphs).

### Step 3 — Translate CSS → Tailwind utilities

The Designer ships `.btn`, `.card`, `.cd-svc`, `.dash-side`, `.adm-side` etc. The port rule:

| Designer pattern | Tailwind equivalent |
|---|---|
| `.btn.btn-dark` | `inline-flex items-center justify-center gap-2 rounded-lg bg-ink-900 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-ink-800` |
| `.btn.btn-accent` | `... bg-brand-600 hover:bg-brand-700 text-white` |
| `.btn.btn-outline` | `... border border-ink-200 bg-white text-ink-900 hover:bg-ink-50` |
| `.card` / `.cd-card` | `rounded-2xl border border-ink-200 bg-white p-6 shadow-sm` |
| `.kicker` / pill | `inline-flex items-center gap-2 rounded-full border border-ink-200 bg-white px-3 py-1 text-xs font-medium text-ink-600` |
| `.dash-side` (provider) / `.adm-side` (admin) | grid `md:grid-cols-[240px_1fr]` + `<aside>` with `border-r border-ink-150 bg-white` |
| `.hero-grid` background dots | The `.hero-grid` class is already in `globals.css` — reuse. |

Anything keyframe-animated (`ray-pulse`, `ray-fade-up`) is already in `globals.css`. Track-view live map's `.track-pulse` and `.live-banner` animations need to be added to `globals.css` once — not inlined per component.

### Step 4 — Move hardcoded data into `lib/mock/*`

Every `dash-data.jsx` / `cdash-data.jsx` / `admin-data.jsx` becomes a single `.ts` file. Shape:

```ts
// web/portal/lib/mock/customer.ts
import type { Appointment, Vehicle } from "@/lib/api/types";

export const MOCK_HOME = {
  greeting: { name: "Alex", tier: "Gold" },
  nextAppointment: { /* ... */ } satisfies Appointment | null,
  garage: [/* ... */] satisfies Vehicle[],
  // ...
} as const;
```

Two non-negotiable rules so the data session can swap cleanly:

1. **One mock file per dashboard surface** (`customer.ts`, `provider.ts`, `admin.ts`). Never inline mock objects inside components.
2. **Every mock shape must `satisfies` a real API type from `@/lib/api/*`.** That guarantees the data session swaps `import { MOCK_HOME } from "@/lib/mock/customer"` for `const data = await getCustomerHome()` with zero downstream type churn.

When the API type doesn't exist yet (e.g. rewards, subscriptions) define a placeholder type in `@/lib/api/types.ts` and flag it with a `// TODO(plan-13)` comment so the data session sees it.

### Step 5 — Wire i18n (portal only)

Portal is `next-intl`. Every user-visible string lands under a namespace matching the route:

- `clientHome`, `clientBookings`, `clientTrack`, `clientGarage`, `clientRewards`, `clientAccount` (already partially seeded in [`messages/en.json`](../../web/portal/messages/en.json)).
- `detailerHome`, `detailerJobs`, `detailerSchedule`, `detailerEarnings`, `detailerCustomers`, `detailerReviews`, `detailerServices`.
- `customerSignup`, `customerLogin`, `providerSignup`, `providerLogin`.

Mirror every EN key to `messages/es.json` before merging. Admin (`web/admin/`) has no i18n — strings stay literal.

### Step 6 — Visual QA + type check

After each wave: `npm run dev:portal` (or `:admin`), open every route, compare side-by-side with the Designer HTML opened in a second browser tab via:

```
file:///c:/Users/yampi/Documents/Projects/raycarwash-project/raycarwash/project/Customer%20Dashboard.html
```

Then `npx tsc --noEmit` in both `web/portal/` and `web/admin/`. Tests in `__tests__/` (where they exist) must still pass.

---

## 4. Wave breakdown

Waves are sized to land independent PRs. Each wave produces one PR; route slugs and mock-file names are stable across waves so the data-wiring session can checkpoint between them.

### Wave 1 — Foundations (S, ~1 day)

1. Mirror Tailwind theme tokens into `web/admin/app/globals.css` (add `brand-*`, `ink-*`, `font-display`, `font-mono` for JetBrains).
2. Add JetBrains Mono via `next/font/google` to `web/admin/app/layout.tsx` and `web/portal/app/[locale]/layout.tsx` (admin needs it for the Bits panel mono digits; portal needs it for the receipt component).
3. Promote `.hero-grid`, `.ray-pulse`, `.ray-fade-up` (already in portal globals) + new `.track-pulse`, `.live-banner-pulse` keyframes into both apps' `globals.css`.
4. Create `web/portal/lib/mock/` (empty package, with one stub file `index.ts` re-exporting nothing) and `web/admin/lib/mock.ts` (empty `export {}` placeholder). Plan 11/13/24's data session deletes these by swapping imports.
5. Create the `components/icons/{customer,provider}.tsx` index files that re-export from `lucide-react` for all icons the Designer uses, plus port only the icons not present in `lucide-react` (verify each — most have a 1:1 match).

**Exit criteria:** both apps still build with `npm run build`, no visible regressions.

### Wave 2 — Auth pages (M, ~2-3 days)

Port the 5 auth flows. Reuse `web/portal/components/auth/RoleToggle.tsx` and the existing `GoogleButton` / `GoogleAuthProvider` — don't reinvent Apple/Google buttons.

1. Extract `auth-bits.jsx` → `components/auth/{TextField,PasswordField,OtpInput,StepProgress}.tsx` (portal). Drop `DemoNav` entirely.
2. Replace `(auth)/login/page.tsx` with the audience-aware customer/provider login (single page; toggle via `RoleToggle`, which already exists).
3. Replace `(auth)/signup/page.tsx` with the 5-step customer signup. Mount it as a stepper — each step is `?step=1..5` query param so back/forward survives reload. Wire steps 1-2 to existing `/auth/identify` → `/auth/verify`; steps 3-5 land hardcoded (data session connects to `/api/v1/vehicles`, `/api/v1/users/me/addresses`, `/api/v1/promo/redeem`).
4. Create `(auth)/signup/role/detailer/page.tsx` + `(auth)/onboarding/detailer/{step1,step2,step3,step4,step5,step6,step7}/page.tsx` — 7-step provider signup wizard. Each step renders the panel from `provider-signup.jsx`; submission lands `useState` only (Plan 24 owns backend).
5. Port `staff-login.jsx` to `web/admin/app/login/page.tsx`. This is a *security-sensitive* flow — the current admin login uses a hardcoded `loginAdmin()` call in `web/admin/lib/auth.ts`. Keep that wiring; only the visual layer changes.

**Exit criteria:** every page renders in `npm run dev:portal` and `dev:admin`; `tsc --noEmit` clean in both; `RoleToggle` still works end-to-end on `/login`.

### Wave 3 — Customer Dashboard (M, ~3-4 days)

1. Build `CustomerShell` once (sidebar + topbar + main slot + tier badge + "Book a wash" CTA).
2. Translate `cdash-data.jsx` → `lib/mock/customer.ts` (with `satisfies` against `@/lib/api/{appointments,vehicles,users}/types.ts`). Define placeholder types `Reward`, `Subscription`, `LoyaltyTier`, `Favorite` in `lib/api/types.ts` flagged `TODO(plan-13)`.
3. Port the 6 views in order: `home` (most reused widgets), `bookings`, `track`, `garage`, `rewards`, `account`.
4. The track view's live-map uses an SVG with `.track-pulse` and `.live-banner` — these are pure CSS animations, no map library needed. Real map integration is Plan 13's job.
5. Reuse `useVehicles`, `useAppointments`, `useMe` hooks where the data is real (vehicles, appointments). For rewards/subscriptions/favorites/recommendations, import from `lib/mock/customer.ts` and add a `TODO(plan-13)` comment on the import.

**Exit criteria:** every route under `(app)/client/*` renders Designer-parity; mobile layout matches the designer breakpoints (uses `md:` + `lg:` consistently).

### Wave 4 — Provider Dashboard (L, ~4-5 days)

Largest wave because of `dash-services.jsx` (493 LOC, 5 sub-views).

1. Build `ProviderShell` (sidebar with 3 nav groups: Workspace / Business / Account; topbar with online/offline toggle + notifications popover + "New job" pulse CTA).
2. Translate `dash-data.jsx` → `lib/mock/provider.ts`. Add placeholder types `EarningsSeries`, `JobOffer`, `Customer` (CRM), `ScheduleSlot`, `Service`, `Addon`, `RouteStop` — all flagged `TODO(plan-11)`.
3. Port views in order of UI complexity: `overview` (KPI grid + chart), `jobs` (offer accept/decline cards), `schedule` (week grid), `earnings` (chart + breakdown), `customers` (CRM table), `reviews` (list), `services` (5-tab tabbed view).
4. The `services` view is large because it has its own internal nav. Keep it as **one route file** that switches between sub-views via local state (Designer pattern) — matches the visual flow and avoids 5 extra route folders.
5. Notifications popover: extract from `dash-shell.jsx` into `components/app/NotificationsPopover.tsx`. Data is `lib/mock/provider.ts.notifications`. Same with the "New job" CTA modal.

**Exit criteria:** `(app)/detailer/*` routes all render Designer-parity; `tsc --noEmit` clean; chart renders without external library (Designer uses inline SVG bars — keep that, don't pull in Recharts).

### Wave 5 — Admin Dashboard (L, ~4-5 days)

1. Create `web/admin/components/{Shell,Header,Bits,icons}.tsx`. The current `sidebar.tsx` is replaced by `Shell.tsx`. **Delete** `sidebar.tsx` only after `Shell.tsx` is the layout child of `app/dashboard/layout.tsx`.
2. Translate `admin-data.jsx` → `web/admin/lib/mock.ts`. Mock data includes: live appointment list with status, detailer roster, customer roster, finance figures (gross, net, payouts, refunds), city allowlist, marketing campaigns, support tickets. Flag all with `TODO(plan-24)`.
3. Port the 11 views. The current `dashboard/{users,roles,permissions,verifications,payments,appointments}` are kept (Plan 24 backend is shipping to them) — but their **visual layer is replaced** by the Designer's bookings/detailers/customers/finance/support equivalents. Map: `users` → keep (admin's user mgmt) but restyle with new `Bits`; the Designer's `bookings/detailers/customers` become *separate* dashboard routes living alongside.
4. Ops view (`admin-ops.jsx` → `dashboard/page.tsx`) becomes the new landing. Old stat-card overview is deleted in this PR.
5. **Do not** wire any new admin API call in this wave — the data session (Plan 24 Wave 2+) owns endpoint mapping for the new admin routes.

**Exit criteria:** `npm run dev:admin` shows the Designer Ops dashboard at `/dashboard`; every new view renders with mock data; `tsc --noEmit` clean.

---

## 5. Hand-off contract with the data session

The data session (other branch / other agent) reads `lib/mock/*.ts` and replaces each named export with a real fetcher. The contract:

| Surface | Hand-off file | Real fetchers that should swap in | Existing plan |
|---|---|---|---|
| Customer Dashboard | `web/portal/lib/mock/customer.ts` | `useCustomerHome()`, `useRewards()`, `useFavorites()`, `useSubscriptions()` | [13](./13-customer-dashboard.md) |
| Provider Dashboard | `web/portal/lib/mock/provider.ts` | `useProviderKPIs()`, `useJobOffers()`, `useEarningsSeries(14)`, `useSchedule(weekStart)`, `useCustomerCRM()`, `useServiceCatalog()` | [11](./11-provider-dashboard.md) + [20](./20-api-contracts-track2-provider-dashboard.md) |
| Admin Dashboard | `web/admin/lib/mock.ts` | `useAdminOps()`, `useAdminBookings(...)`, `useAdminFinance(...)`, plus 8 more views' fetchers | [24](./24-auth-pages-and-admin-dashboard.md) |
| Customer Signup (steps 3-5) | inline `useState` in `(auth)/signup/page.tsx` | `POST /api/v1/vehicles` (exists), `POST /api/v1/users/me/addresses` (exists), `POST /api/v1/promo/redeem` (Plan 24 C-2) | [24](./24-auth-pages-and-admin-dashboard.md) §2 |
| Provider Signup (7 steps) | inline `useState` in onboarding stepper | KYC (Plan 24 P-1), Checkr (P-2), document upload (P-3), Plaid (P-4), equipment (P-5) | [24](./24-auth-pages-and-admin-dashboard.md) §3 |

**Invariant the data session relies on**: every `MOCK_*` export in `lib/mock/*` already matches the real backend shape via `satisfies`. If a placeholder type was used, it carries `TODO(plan-NN)`. The data session greps for `TODO(plan-` to find them.

---

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Two parallel branches (frontend port + data wiring) collide on the same files | The mock-file boundary (§3 Step 4) is the *only* shared file. Frontend wave PRs touch route files + components; data PRs touch hooks + mock imports. Document hand-off in PR description. |
| Designer ships another revision while we're mid-port | Re-run the skill's diff step (`~/.claude/skills/frontend/designer_to_next.md` §6) — it lists which JSX file changed and what to re-extract. Routes & mock shapes stay stable. |
| Admin app dependency on `next/font` (Geist) clashes with new JetBrains Mono | Keep Geist as `--font-geist-sans`, add JetBrains Mono as `--font-mono`. Both apps already use the `next/font/google` pattern. |
| Subroutes inside `dash-services.jsx` tempt us to over-split | §4 Wave 4 step 4 keeps it one route file — match Designer's mental model. Don't fragment for fragmentation's sake. |
| Provider signup 7-step wizard interacts with onboarding tokens | The existing `(auth)/onboarding/detailer/page.tsx` already exists with the auth-flow plumbing. New steps mount underneath; don't replace the layout that owns the `onboarding_token`. |
| Plan 12's `useAudienceStore` collides with new auth pages | Auth pages don't read audience — they have their own RoleToggle that writes `roleIntent` to `useAuthStore`. Keep these stores independent. |

---

## 7. What "done" looks like

- [ ] Wave 1 merged: tokens, fonts, mock packages bootstrapped, both apps still build
- [ ] Wave 2 merged: 5 auth pages render Designer-parity; existing auth flows still work
- [ ] Wave 3 merged: customer dashboard 6 views render with mocks; `tsc --noEmit` clean
- [ ] Wave 4 merged: provider dashboard 12 views render with mocks; `tsc --noEmit` clean
- [ ] Wave 5 merged: admin dashboard 11 views render with mocks; `tsc --noEmit` clean
- [ ] [`html-design-analysis.md`](../html-design-analysis.md) updated: each row marked "✅ ported" with link to the Next route
- [ ] Skill [`~/.claude/skills/frontend/designer_to_next.md`](file://C:/Users/yampi/.claude/skills/frontend/designer_to_next.md) used + reviewed end-to-end by at least one wave's author
- [ ] Data session can now start swapping mock imports — every `lib/mock/*` export matches a real (or `TODO(plan-NN)`-flagged) API type via `satisfies`

---

## 8. References

- Inventory and gap analysis: [`docs/html-design-analysis.md`](../html-design-analysis.md)
- Marketing precedent (the *how* of porting a Designer drop): [`docs/plans/12-marketing-redesign.md`](./12-marketing-redesign.md) §0 "What shipped"
- Backend plans the data session pulls from: [11](./11-provider-dashboard.md), [13](./13-customer-dashboard.md), [24](./24-auth-pages-and-admin-dashboard.md)
- API contracts: [19](./19-api-contracts-track1-marketing.md), [20](./20-api-contracts-track2-provider-dashboard.md), [21](./21-api-contracts-track3-customer-dashboard.md)
- The reusable protocol: [`~/.claude/skills/frontend/designer_to_next.md`](file://C:/Users/yampi/.claude/skills/frontend/designer_to_next.md)
