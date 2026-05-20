# 24 — Auth Pages + Admin Dashboard Backend

> **Status:** Planning
> **Priority:** High
> **Dependencies:** Plan 22 (audit reconciliation), Plan 23 (session hardening),
>   m_019 (Stripe Connect columns)
> **Design source:** Claude Design handoff package
>   `V7ZaB-TqHgbIdmu71U-CAQ` → re-shared as `GdvLRdskTDKmGs8lVsr46Q`.
>   12 HTML pages + 17 admin-*.jsx + 5 auth-*.jsx + auth.css + admin.css.
> **Out of scope:** frontend implementation (lives in `web/admin/`,
>   `web/portal/`); this plan covers backend work only.

---

## 1. Pages Inventory

The design package introduces 6 new pages on top of the 6 marketing
pages already shipped (Plan 19 Track 1):

| # | Page | File | Backend bucket |
|---|------|------|----------------|
| 1 | Customer Login | `Customer Login.html` + `customer-login.jsx` | auth (existing) |
| 2 | Customer Signup | `Customer Signup.html` + `customer-signup.jsx` | auth + vehicles + addresses (existing, light extension) |
| 3 | Provider Login | `Provider Login.html` + `provider-login.jsx` | auth (existing, role-gated) |
| 4 | Provider Signup | `Provider Signup.html` + `provider-signup.jsx` | **major new** — KYC + Checkr + Plaid + equipment |
| 5 | Staff Login | `Staff Login.html` + `staff-login.jsx` | auth (existing) + step-up for staff routes |
| 6 | Admin Dashboard | `Admin Dashboard.html` + 14 admin-*.jsx | **major new** — 11 views, mostly new endpoints |

---

## 2. Customer Login & Signup — Backend Mapping

The customer auth flow consumes endpoints that **already exist**. Most
of the work is frontend orchestration; the backend gaps are small.

### 2.1 Customer Login (`customer-login.jsx`)

Two modes: email/password OR phone (OTP). Plus social (Apple/Google).

| Frontend action | Existing endpoint | Backend gap |
|---|---|---|
| Email + password sign-in | `POST /auth/identify` → `POST /auth/verify` | none |
| Phone + OTP sign-in | `POST /auth/identify` (phone) → SMS OTP → `POST /auth/verify(code)` | SMS adapter exists (`infrastructure/sms/twilio.py`); verify the OTP path runs end-to-end |
| Apple Sign-In | `POST /auth/social/apple/verify` (per AGENTS.md social flow) | none |
| Google Sign-In | `POST /auth/social/google/verify` | none |
| "Forgot password" | `POST /auth/password/reset-request` (existing) | none |
| "Keep me signed in" toggle | Maps to refresh-token TTL (currently 7d) | optional: configurable TTL based on the checkbox |

**Decision:** ship the page against the existing endpoints. No new backend.

### 2.2 Customer Signup (`customer-signup.jsx`) — 5 steps

| Step | Frontend collects | Backend endpoint |
|------|-------------------|------------------|
| 1. Account | first_name, last_name, email, password | `POST /auth/identify` + `POST /auth/verify` → onboarding_token |
| 2. Phone OTP (skippable) | phone + 6-digit code | `POST /auth/identify(phone)` → SMS → `POST /auth/verify` updates user.phone |
| 3. Vehicle (skippable) | year, make, model, color, plate | `POST /api/v1/vehicles` (existing) — but design shows a price-estimate preview after entry: needs cheap lookup |
| 4. Address | line, apt, city, state, zip | `POST /api/v1/users/me/addresses` (existing) + `POST /api/v1/public/coverage/check` to validate ZIP coverage (existing — Plan 19 §4) |
| 5. Welcome (with $10 promo) | Display `NEW10` code | Static UI — but the code needs server-side validation later when applied at checkout |

#### Backend gaps for customer signup

| # | Gap | Effort | Priority |
|---|-----|--------|----------|
| C-1 | `GET /api/v1/vehicles/price-estimate?year=&make=&model=` — quick price preview for the Step 3 success card (mid-size SUV → $179 full detail). Today the catalogue prices are per-vehicle-size, derived at booking time. Needs a lightweight "given vehicle metadata, estimate VehicleSize + show price tiers" endpoint. | Small | Medium |
| C-2 | `NEW10` promo code persistence — design auto-applies a $10 welcome credit. Needs a `promo_codes` table + `applied_promo_codes` per user. | Medium | Medium |
| C-3 | Address ZIP gate — block address save if ZIP isn't in `coverage_zips`. Today `POST /addresses` accepts any ZIP. | Small | Low |

---

## 3. Provider Login & Signup — Backend Mapping

Provider login is symmetric to customer login (same `/auth/*` endpoints,
role-gated). **Provider signup is the major net-new backend work** —
7 steps with KYC, background checks, document upload, and bank linking.

### 3.1 Provider Login (`provider-login.jsx`)

Same auth endpoints as customer login. Behaviour difference: the JWT
returned must carry the `detailer` role, and the dashboard route should
return 403 for `client`-only users.

**Backend gap:** none. `require_role("detailer")` exists.

### 3.2 Provider Signup (`provider-signup.jsx`) — 7 steps + welcome

| Step | Frontend collects | Backend endpoint(s) |
|------|-------------------|---------------------|
| 1. Account | email + password + ICA consent | `POST /auth/identify` + `POST /auth/verify` → onboarding_token |
| 2. About you | legal_first_name, legal_last_name, phone, dob, **ssn_last_4** | `PUT /api/v1/providers/profiles` — extend with ssn_last_4 |
| 3. Service area | home_city (5 cities), travel_radius (3-25 mi) | `PATCH /api/v1/users/me/provider-profile` — `service_radius_miles` exists; needs `home_city_code` |
| 4. Vehicle & gear | work_vehicle, **water_tank_size** (0/20/40/60), **services_offered** (soap/vacuum/polish/ceramic) | NEW columns on `provider_profiles` + `POST /api/v1/users/me/provider-portfolio` for the vehicle photo |
| 5. Background check consent | bg_consent | Checkr integration (TODO) — currently Stripe Identity covers ID verification but not full bg check |
| 6. Documents (DL/insurance/photo/business) | file uploads | `POST /api/v1/users/me/provider-documents` (existing) — verify it supports the 4 doc types |
| 7. Payouts | Plaid link OR manual routing/account | Plaid integration (TODO) — Stripe Connect (m_019) covers payouts; bank-account-on-file isn't currently captured |
| 8. Welcome | application status timeline | `GET /api/v1/users/me/provider-verification` (existing) — surfaces 3-step status |

#### Backend gaps for provider signup

| # | Gap | Migration / endpoint | Effort | Priority |
|---|-----|----------------------|--------|----------|
| **P-1** | `provider_profiles.ssn_last_4` (encrypted column, used once by background check then forgotten) | Future M24 — `ssn_last_4_encrypted VARCHAR encrypted`. Already have `EncryptedType` pattern via `_provider_encryption_key`. | Small | **High** |
| **P-2** | `provider_profiles.home_city_code` (enum: fwa, ind, col, cin, lou) — multi-city support | Future M25 — `home_city_code VARCHAR(8)` + seed of the 5 cities into a `cities` lookup table | Medium | **High** |
| **P-3** | `provider_profiles.water_tank_gallons` (Integer nullable, 0-60+) + `provider_profiles.services_offered` (JSONB array of service-id slugs) | Future M26 — both columns added to `provider_profiles` | Small | **High** |
| **P-4** | Checkr integration — `/api/v1/users/me/provider-background-check/start` + webhook handler. Today Stripe Identity (`stripe_verification_session_id` exists on `provider_profiles`) does ID verification but isn't a full Checkr report. | New `domains/providers/background_check.py` adapter pattern (like `infrastructure/payments`). | Large | Medium |
| **P-5** | Plaid integration — `/api/v1/users/me/provider-bank/link` (Plaid Link token) + webhook for `LINK_VERIFIED`. Bank account stored encrypted (routing + last-4). Stripe Connect (m_019) handles the actual payout *destination* once the cuenta-conectada is enabled, but the design wants the application to capture bank info **before** the Stripe Connect flow. | New `infrastructure/plaid/` adapter. | Large | Medium |
| **P-6** | `provider_profiles.work_vehicle_year` + `_make` + `_model` + `_plate` — currently the provider's personal vehicle is tracked in `vehicles` table but the **work** vehicle (the van they detail out of) is conceptually different | Reuse `vehicles` with a `kind=work` flag, OR add 4 dedicated columns to `provider_profiles`. Recommend the flag approach to avoid duplication. | Small | Medium |
| **P-7** | `provider_application_status` — enum-like state machine (`draft → submitted → bg_check_pending → docs_review → approved | rejected`). Today `verification_status` covers ID verification but not the full application lifecycle. | Promote `verification_status` to a true state machine + add `application_status` column. | Medium | Medium |

---

## 4. Staff Login — Backend Mapping

`staff-login.jsx` — separate styled page (darker theme, no "create account").

| Frontend action | Backend |
|---|---|
| Email + password sign-in | `POST /auth/identify` + `POST /auth/verify` — same as everyone |
| Role-gated redirect | After login: if `user.has_role("staff")` or `"admin")` → `/admin`; else 403 |
| 2FA challenge (mandatory for staff per design) | Existing TOTP credential infra (`domains/auth/totp_credential.py`) — verify the flow forces enrollment for staff |
| IP allowlist (design implies "office network only") | Not in scope; document as future enhancement |

#### Backend gaps for staff login

| # | Gap | Effort | Priority |
|---|-----|--------|----------|
| S-1 | `staff` role distinction from `admin`. Today there's only `admin`. The design has both ops/support staff (limited) and admin (full). Add `staff` as a Role row + map admin endpoints to `require_role("staff", "admin")` where appropriate. | Small | Medium |
| S-2 | Mandatory TOTP enrollment for staff. Today TOTP is opt-in for all users. Add a `enforce_totp` flag on Role, blocking sign-in until enrolled. | Medium | Medium |

---

## 5. Admin Dashboard — 11 Views Mapping

`admin-data.jsx` has 19 top-level data shapes. Most map to **new**
admin endpoints; some reuse existing ones.

### 5.1 View → Endpoint mapping

| View | Endpoint(s) needed | Existing? |
|------|-------------------|-----------|
| **Operations overview** | `GET /api/v1/admin/ops/dashboard` (KPIs, heatmap 7d×24h, surge overlay, live feed, alerts, detailer utilization per city) | **New** — partially reuses `appointments`, `provider_profiles` aggregates |
| **Live map** | `GET /api/v1/admin/ops/live-map` (active jobs with detailer locations + status pins) | **New** |
| **Bookings management** | `GET /api/v1/admin/appointments` (filter+pagination) — extend existing admin endpoints with refund/reassign actions | Partial — admin appointment listing exists; force-cancel exists via `PATCH /admin/appointments/{id}/status`; refund + reassign need explicit endpoints |
| **Support inbox** | `GET /api/v1/admin/support/threads` + `GET /threads/{id}` + `POST /threads/{id}/reply` | **New** — needs `support_threads`, `support_messages` tables |
| **Detailers** | `GET /api/v1/admin/detailers` + `POST /{id}/approve` + `POST /{id}/suspend` + `GET /{id}/performance` | Partial — admin detailer listing exists; approve/suspend actions need to be wired |
| **Customers** | `GET /api/v1/admin/customers` (search, segments) + `POST /{id}/credits` (issue comp) + `GET /{id}/tickets` | Partial — listing exists; segments + credits are new |
| **Reviews moderation** | `GET /api/v1/admin/reviews/queue` (flagged) + `POST /{id}/approve|hide` | **New** — needs `review_flags` table; flag triggers (low rating, profanity) |
| **Cities & zones** | `GET /api/v1/admin/cities` + `GET /api/v1/admin/zones` + `PUT /zones/{id}` + `POST /surge-rules` | **New** — multi-city support needs `cities` lookup table + `surge_rules` |
| **Finance** | `GET /api/v1/admin/finance/dashboard` (GMV, take rate, payouts, fees, disputes) | **New** — aggregates over `appointments`, payments ledger (m_007), Stripe payouts |
| **Marketing** | `GET /api/v1/admin/promo-codes` + CRUD; `GET /referrals/program` config | **New** — needs `promo_codes` + `referrals` tables |
| **Settings & team** | `GET /api/v1/admin/team` + roles/permissions + audit log | Partial — RBAC exists; team listing reuses `users` filtered by role |

### 5.2 New tables for admin dashboard

| # | Table | Purpose | Used by | Migration |
|---|-------|---------|---------|-----------|
| **A-1** | `cities` | Multi-city configuration (id, code, name, state, timezone, status: active/pilot/planned) | All views (city switcher) | Future M27 |
| **A-2** | `service_zones` | Geographic zones within a city (id, city_id, name, polygon, demand_tier, status) | Cities & zones view + matching | Future M28 |
| **A-3** | `surge_rules` | Time-windowed surge multipliers per zone (zone_id, day_of_week, hour_start, hour_end, multiplier, status) | Operations heatmap + finance pricing | Future M29 |
| **A-4** | `support_threads` + `support_messages` | Customer/detailer support tickets with conversation history | Support inbox view | Future M30 |
| **A-5** | `review_flags` | Reviews flagged by rules (low rating, profanity keyword hit, customer dispute) | Reviews moderation view | Future M31 |
| **A-6** | `promo_codes` + `applied_promo_codes` | Marketing promo code campaigns + per-user redemption tracking | Marketing view + checkout | Future M32 |
| **A-7** | `referrals` | Referral program tracking (referrer_user_id, referee_user_id, code, status, reward_cents) | Marketing view + signup | Future M33 |
| **A-8** | `customer_credits` | Comp credits issued by support (user_id, amount_cents, reason, expires_at, applied_at) | Customers view + checkout | Future M34 |

### 5.3 Admin dashboard cross-cutting gaps

- **Multi-city aware audit log** — every mutation should log `city_id` so the dashboard can filter by city.
- **Detailer location streaming** — Live map needs detailer GPS coordinates updated in real-time. Today `provider_profiles` has `current_lat/lng` but no recent-update guarantees. Need a worker / WebSocket from the mobile app.
- **Heatmap data source** — `heat[][]` is 7d×24h demand intensity. Compute as a materialised view over `appointments.scheduled_time` bucketed by hour, refreshed every 15 min.
- **Live feed** — terminal-style stream of events. Map to the existing audit log filtered to `entity_type IN ('appointment', 'payment', 'review')` with last-N-events SSE/WebSocket.

---

## 6. Implementation Order

The total scope is huge (~30 new endpoints, ~8 new tables, 2-3 third-
party integrations). Recommended slicing:

### Wave 1 — Auth pages backend (frontend can ship)
- **S-1** Add `staff` role distinction
- **P-7** Promote `verification_status` → state machine + `application_status`
- **P-1** `ssn_last_4_encrypted` column on `provider_profiles` + signup endpoint accepts it
- **P-3** `water_tank_gallons` + `services_offered` columns
- **P-2** + **A-1** `cities` table + `home_city_code` on profile
- **C-1** Vehicle price-estimate endpoint
- **C-3** Address ZIP gate

**Outcome:** Customer + Provider + Staff login/signup pages are fully
wireable against the backend. Provider signup steps 5 (Checkr) and 7
(Plaid) remain manual review fallbacks until Wave 3.

### Wave 2 — Admin dashboard MVP (5 most-used views)
- Operations overview endpoint (KPIs + heatmap from existing data)
- Bookings management (extend admin endpoints with refund + reassign)
- Detailers approve/suspend/performance
- Customers segments + credits issue
- Reviews moderation queue + approve/hide

**Outcome:** Admin staff can run day-to-day ops. Live map, support
inbox, surge config, finance dashboard, marketing CMS deferred.

### Wave 3 — Integrations & advanced admin
- Checkr background check adapter (P-4)
- Plaid bank linking (P-5)
- Live map with detailer GPS streaming
- Support inbox tables + endpoints
- Surge rules engine
- Marketing CMS (promo codes, referrals, campaigns)
- Customer credits / comp issuance flow

**Outcome:** Full feature parity with the design package.

### Wave 4 — Polish & hardening
- C-2 promo code persistence + redemption flow
- A-3 surge rules → matching engine
- A-8 customer credits → checkout
- Heatmap materialised view + 15-min refresh worker
- Real-time live feed via WebSocket / SSE

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| Checkr + Plaid are paid third-party integrations with onboarding lead time | Document fallback (manual review by staff) and gate Wave 3 behind procurement |
| Provider signup multi-step has many partial-completion states | Build a `provider_application_drafts` cache table; UI saves on each step to avoid losing progress |
| `staff` vs `admin` role split risks regressing existing admin endpoints | Migrate endpoint-by-endpoint with feature flags; default to `require_role("admin")` and broaden to `("staff", "admin")` only after coverage review |
| Live map GPS streaming needs mobile app cooperation | Document the mobile contract (frequency, accuracy) before spending backend effort |
| Multi-city support cascades to a lot of code (matching, pricing, audit) | Land `cities` table early, but keep `Fort Wayne` as the only active city until ops is ready |
| Admin dashboard data volumes will be large | Build with pagination + caching from day 1 — don't trust the design's "load all 1000 bookings" prototypes |

---

## 8. Dependencies

| Plan | Relation |
|------|----------|
| `22-security-architecture-audit.md` | All new auth endpoints inherit the H1 idempotency fix + envelope shape. |
| `23-auth-hardening.md` | Provider/customer signup creates real `Session` rows (Fase 1 day 2-3 dependency). Staff login enforces step-up TOTP. |
| `19-api-contracts-track1-marketing.md` | `POST /public/coverage/check` is reused by customer signup ZIP gate (C-3). |
| `20-api-contracts-track2-provider-dashboard.md` | Provider dashboard is the destination after signup; this plan's signup must produce profile data that dashboard renders correctly. |
| `21-api-contracts-track3-customer-dashboard.md` | Customer dashboard is the destination after signup. |
| `m_019_provider_profiles_stripe_connect` | Plaid bank linking + payouts use Stripe Connect columns already in place. |

---

## 9. Open Questions

- **Promo code `NEW10`** — is this the actual code we want to ship, or a placeholder? Persist as a single `welcome_credit` rule, or as a full promo_codes table from day one?
- **Phone OTP for customers** — Twilio adapter exists but actual SMS sending isn't enabled in production. Decision needed before customer signup goes live.
- **Checkr vs alternative** — design mentions Checkr by name (with their UI). Is procurement of Checkr in flight, or should we evaluate Sterling/Onfido?
- **Plaid vs Stripe Financial Connections** — Stripe also offers bank account verification under Stripe Connect. Could avoid a second integration. Worth confirming with finance.
- **Staff IP allowlist** — design doesn't show it, but for an internal tool it's standard. Add now or defer?

---

## 10. Next Implementation Step

Start with **Wave 1 / item S-1** (add `staff` role distinction). It's
the smallest possible change that unblocks the next chunk
(`require_role("staff", "admin")` adoption) and has zero cross-domain
ripple. Follow with P-1/P-3/A-1 (provider signup column additions +
cities table) as a single migration M24.

Subsequent steps proceed per §6 wave order.

---

## 11. Implementation Status (live tracker)

> Updated 2026-05-19 — refreshes per commit. Items reference §3/§5 IDs.

### Wave 1 — Auth pages backend

| ID | Item | Status | Commit |
|----|------|--------|--------|
| **S-1** | `staff` Role distinct from `admin` (RBAC seed + permissions) | ✅ Done | `909a23e` |
| **P-1** | `provider_profiles.ssn_last_4_encrypted` column + PATCH accepts `ssn_last_4` | ✅ Done | `909a23e` schema · `da92957` API |
| **P-2** | `home_city_code` column + `cities` lookup + active-city validation on PATCH | ✅ Done | `909a23e` schema · `da92957` API |
| **P-3** | `water_tank_gallons` + `services_offered` columns + PATCH wired (Literal enum on skills) | ✅ Done | `909a23e` schema · `da92957` API |
| **P-7** | `application_status` column + `POST /provider-profile/submit` (draft → submitted) | ✅ Column + submit shipped (admin-approval transitions still pending) | `909a23e` schema · `6fa9fef` submit endpoint |
| **A-1** | `cities` table + `City` ORM + 5-city seed (fwa active; ind/col/cin/lou pilot) | ✅ Done | `909a23e` |
| **P-6** | Work vehicle vs personal vehicle distinction | ⏳ Pending | — |
| **P-4** | Checkr background-check adapter | ⏳ Pending (Wave 3) | — |
| **P-5** | Plaid bank-link adapter | ⏳ Pending (Wave 3) | — |
| **C-1** | `GET /api/v1/vehicles/price-estimate` (anonymous, model-keyword size heuristic, 2 anchor tiers) | ✅ Done | `3aa4b25` |
| **C-2** | `NEW10` welcome promo persistence | ⏳ Pending (Wave 4) | — |
| **C-3** | ZIP gate on `POST /api/v1/users/me/addresses` | ⏳ Pending | — |
| **S-2** | Mandatory TOTP enrollment for staff role | ⏳ Pending | — |

### Wave 2 — Admin dashboard MVP

| ID | Item | Status |
|----|------|--------|
| Operations overview aggregate endpoint | ⏳ Pending | — |
| Bookings management (refund + reassign actions) | ⏳ Pending | — |
| Detailers approve/suspend/performance | ⏳ Pending | — |
| Customers segments + comp credits | ⏳ Pending | — |
| Reviews moderation queue + approve/hide | ⏳ Pending | — |

### Migrations landed for this plan

| Migration | Adds | Status |
|-----------|------|--------|
| `m_024_cities_table_and_provider_signup_fields` | `cities` table + 5 columns on `provider_profiles` | ✅ Applied |

### Test coverage added

| File | Tests | Notes |
|------|-------|-------|
| `tests/test_users_provider_profile.py` | 4 new (14 total) | P-1/P-2/P-3 PATCH happy path + city validation + SSN regex + skill enum |
| Seed smoke test | inline | `seed_cities` inserts 5 rows + idempotent re-run |
