# 11 — Provider Dashboard (Full Backend & Frontend Plan)

> **Status:** Planning · supersedes prior 11 draft after full design analysis
> **Priority:** High
> **Dependencies:** `09-provider-services-integration.md` (services catalog), `10-authorization-layer.md` (provider scope), `15-marketing-content-cms.md` (shared content APIs)
> **Audit findings resolved:** N/A
> **Design source:** `raycarwash/project/Provider Dashboard.html` + 12 JSX files (`dash-app/icons/data/shell/overview/jobs/schedule/earnings/customers/reviews/services` + 5 sub-views inside `dash-services.jsx`)

---

## 1. Objective

Ship the full provider dashboard at `web/portal/[locale]/(app)/detailer/dashboard/*` (portal app (port 3001)) matching the high-fidelity design in `raycarwash/project/`. The dashboard has **12 distinct views** organized into 3 sidebar groups:

| Group | Views |
|---|---|
| **Workspace** | Overview · Jobs · Schedule · Today's route |
| **Business** | Earnings · Customers · Reviews · Services & pricing · Supplies |
| **Account** | Profile · Settings · Help |

Plus a **global app-shell** with sidebar nav, search, notifications popover, online/offline toggle, and "new job" CTA — all reactive to live data.

The prototype is **fully populated with mock data in `dash-data.jsx`**. This plan maps every mock field to a backend source and identifies what must be built.

---

## 2. Hardcoded data inventory (from `raycarwash/project/src/dash-data.jsx`)

Every field below currently lives in mock JavaScript and must flow from backend APIs in production.

### 2.1 `me` — provider identity
```
name, initials, role ("Detailer · L3 Pro"), tier ("Gold"),
rating (4.92), jobs (312), onTime (98), member ("Jan 2024")
```
**Source**: `users.me` + `provider_profiles.{tier, on_time_pct, member_since}` + derived `(rating, jobs)` from reviews & appointments.

### 2.2 `kpis` — 8 dashboard KPIs (current + delta)
| Key | Mock value | Computation |
|---|---|---|
| `todayJobs` | 5 (Δ +2, +25%) | `count(appointments where provider=me AND day=today)` vs same weekday avg |
| `todayEarnings` | $412 (Δ +$78, +18%) | `sum(net_pay) where appointment.completed_at=today` |
| `weekEarnings` | $2,148 (Δ +$312, +15%) | rolling 7-day sum vs prior 7 days |
| `monthEarnings` | $8,642 (Δ −$428, −4.7%) | rolling 30d sum vs prior 30d |
| `rating` | 4.92 (Δ +0.04) | last-30d avg vs prior-30d avg |
| `completion` | 98% (Δ +1) | `completed / (completed + cancelled_by_detailer + no_show)` |
| `avgTicket` | $153 (Δ +$7) | mean `appointment.actual_price_cents` |
| `response` | 1.4 min (Δ −0.3) | mean (`job_offer.responded_at` − `job_offer.created_at`) |

### 2.3 `earnings14d` — daily earnings series
14 days × `{date, base_cents, tips_cents}`. Used by the bar chart + sparkline.

### 2.4 `incoming` — pending job offers
3 mock offers with: `id`, service description, add-ons array, vehicle, location + distance, scheduled time, pay, duration, customer name + rating, `new` flag, `surge` flag.

### 2.5 `route` — today's 5 stops
Ordered list of today's appointments with status `done | now | next`.

### 2.6 `customers` — 8 CRM-style entries
```
{ id, name, init, color, visits, total_spent_cents, last_visit,
  vip, location, phone }
```
Plus aggregate KPIs: total (142), repeat rate (58%), VIPs (5), avg LTV ($339).

### 2.7 `reviews` — 5 entries + distribution
- Each: `stars`, `when`, `service`, `body`, optional `reply` (string).
- Distribution: 312/28/6/1/1 across 5/4/3/2/1 stars.
- Auto-tagged highlights: ["On time" × 142, "Professional" × 98, …, "Streaks (minor)" × 4, "Late arrival" × 2].
- AI summary paragraph (LLM-generated from review corpus).
- Rank meta: "Top 8% in Fort Wayne".

### 2.8 `services` — 6 catalog entries
```
{ id, name, price_cents, duration_min, active, features[],
  bookings_30d, popular?, addon?, draft? }
```

### 2.9 `payouts` — 9 ledger entries
Mixed types: `in` (job, tip, supply credit), `out` (weekly payout), `fee` (platform fee).
Each: `date`, `label`, `amount_cents`, `kind`.

### 2.10 `notifs` — 5 notification entries
Kinds: `brand`, `ok`, `warn`. Each: `title`, `body`, `time_ago`, `unread`.

### 2.11 `schedule` — 7-day grid
18 events across 7 days, each: `{ day_index, start_hour, end_hour, label, service_text, type ("ok"|"brand"|"warn"|"ghost"|"") }`.
Plus working-hours table (Mon-Sun with on/off + range) and service-zones table (zone name, radius mi, type, surcharge).

### 2.12 `insights` — 3 AI/rule-based tips
```
"You earn 24% more on Saturdays · open 2 more slots Sat morning"
"3 customers haven't rebooked in 60+ days · send 'we miss you' offer"
"Add-on attach rate is 41% · above platform avg (28%)"
```

### 2.13 Earnings sub-data (from `dash-earnings.jsx`)
- Available to cash out ($412 · instant payout $0.50 fee)
- Pending settlement ($786.40 · auto-deposits Friday)
- This month gross + monthly goal % (73%)
- Lifetime earnings + jobs + member date
- 14d gross, platform fee 15%, tips earned, net to bank
- Donut breakdown by service: Full $4520, Interior $1980, Express $880, Ceramic $896, Add-ons $366
- Deposit account: "Chase Checking · ••2847"
- Auto-payout toggle (Every Friday 5pm)
- 2025 tax forms (1099-NEC)
- Estimated tax set-aside (30% of gross, $2,592/month, $1,610 saved, 62% progress)

### 2.14 Services sub-data
- Promo codes: `FIRST20`, `SPRING50`, `REFER15`, `WELCOME10` (with description, uses, status)
- Pricing rules: Travel surcharge / Weekend premium / Same-day booking / Loyalty discount / Group fleet (each: rule, condition, value, on-toggle)

### 2.15 Supplies sub-data (`ViewSupplies`)
7 items: `{ name, stock, par, unit, cost, last_purchase, supplier }`. KPIs: Below par count, Inventory value, Spent 30d, Supply credits.

### 2.16 Profile sub-data (`ViewProfile`)
- Display name, business name, phone, email, bio
- Specialties tag list: Ceramic, Pet hair, Leather, Headlight resto, Boats/RVs
- Verifications & badges: Identity (Onfido), Background, Insurance ($2M State Farm), W-9, IDA cert, Eco-friendly products
- Achievement badges: 300 Jobs, 4.9+ Rating, Quick Responder, Gold Tier
- Portfolio gallery: 8 before/after slots

### 2.17 Settings sub-data (`ViewSettings`)
- Notifications: New job requests, Customer messages, Daily summary, Weekly payout, Reviews, Marketing
- Auto-accept rules: Auto-accept repeat customers, Auto-decline beyond 10 mi, Auto-decline below $40, Snooze
- Security: 2FA, Active sessions, Login alerts, Change password
- Account & data: Export data, Connected apps (QuickBooks, Stripe), Pause account, Delete account

### 2.18 Help sub-data
- Live chat, Call dispatch `(260) 555-WASH`, Email support `pros@raycarwash.com`
- 5 common questions (payouts, platform fee, insurance, cancellation, getting bookings)

---

## 3. Backend gap analysis

### 3.1 What exists today
- `users` + `provider_profiles` (`years_of_experience`, `service_radius_miles`, `bio`, `working_hours`)
- `appointments` (FSM: pending → confirmed → arrived → in_progress → completed/cancelled/no_show)
- `appointments.actual_price_cents`, `estimated_price_cents`, `platform_fee_cents`
- `reviews` (rating, comment, response field)
- `services` catalog (provider_services link table from plan 09)
- `notifications` infrastructure (push only)
- Earnings sum via `GET /api/v1/detailers/me` (single number, no time-series)

### 3.2 What's missing — by view

| View | Endpoints needed | New models |
|---|---|---|
| Overview | `GET /dashboard/overview` (composite) | — |
| Jobs | `GET /jobs?tab=&service=&search=` · `POST /jobs/{id}/accept` · `POST /jobs/{id}/decline` · `POST /jobs/manual` | `JobOffer` (separates offer from appointment) |
| Schedule | `GET /schedule/week?start=` · `POST /schedule/blackout` · `PATCH /working-hours` · `GET/POST /service-zones` | `ProviderBlackoutDate`, `ProviderServiceZone` |
| Route | `GET /route/today` · `POST /route/optimize` · `POST /jobs/{id}/share-eta` | — |
| Earnings | `GET /earnings/summary` · `GET /earnings/series` · `GET /earnings/breakdown` · `GET /earnings/ledger` · `GET /payouts` · `POST /payouts/cash-out` · `PATCH /payout-settings` · `GET /tax-forms` | `Payout`, `PayoutSettings`, `LedgerEntry`, `TaxForm` |
| Customers | `GET /customers?filter=&sort=` · `GET /customers/{id}` · `POST /customers/manual` · `POST /campaigns/winback` | `CustomerSegment` (computed/cached) |
| Reviews | `GET /reviews?filter=` · `POST /reviews/{id}/reply` · `GET /reviews/distribution` · `GET /reviews/highlights` · `POST /reviews/ai-suggest-reply` | `ReviewReply`, `ReviewHighlight`, `ReviewAISummary` |
| Services & pricing | `GET/POST/PATCH /provider-services` · `POST /promo-codes` · `GET /pricing-rules` · `PATCH /pricing-rules/{id}` | `PromoCode`, `PricingRule` |
| Supplies | `GET/POST/PATCH /supplies` · `POST /supplies/reorder` · `POST /supplies/scan-receipt` | `SupplyItem`, `SupplyOrder` |
| Profile | `GET/PATCH /me/profile` · `GET /me/verifications` · `GET/POST/DELETE /me/portfolio` · `GET /me/badges` | `Specialty`, `Verification`, `Badge`, `PortfolioItem` |
| Settings | `GET/PATCH /me/notification-prefs` · `GET/PATCH /me/auto-rules` · `GET /me/sessions` · `POST /me/2fa` · `POST /me/export-request` · `POST /me/pause` · `DELETE /me` | `NotificationPref`, `AutoRule`, `DataExport` |
| Help | `GET /support/articles` · `POST /support/tickets` · `GET /support/status` | `SupportTicket` |
| **Shell** | `GET /notifications` · `POST /notifications/mark-read` · `PATCH /me/online-status` · `GET /search?q=` · `GET /insights` | `Insight`, `OnlineStatus` |

### 3.3 Computed/cached data
| Data | How to compute | Caching strategy |
|---|---|---|
| KPI deltas (vs prior period) | SQL window functions over `appointments` | Redis cache, 5-min TTL, invalidated on appointment status change |
| Earnings 14d series | `SELECT date_trunc('day', completed_at), SUM(actual_price_cents - platform_fee_cents), SUM(tip_cents) GROUP BY day` | Redis cache, 1-hour TTL |
| Customers list (derived from appointments) | `GROUP BY client_id` over completed appointments | Materialized view `provider_customers_mv`, refreshed nightly |
| Repeat rate | `count(client_id where visits >= 2) / count(distinct client_id)` over 60-day window | Computed on demand, cached 1h |
| Top customers by lifetime | `ORDER BY SUM(actual_price_cents) DESC LIMIT 5` per provider | Materialized view |
| Review highlights / AI summary | Claude API call on review corpus | Stored in `review_highlights` table, refreshed weekly |
| Insights | Rule engine (e.g. "Saturday earnings > weekday × 1.2") | Generated by background worker daily, stored in `provider_insights` |
| Win-back targets | Last visit > 60 days ago, LTV > $X | Computed daily by worker |
| "Top 8% in Fort Wayne" rating rank | `PERCENT_RANK() OVER` across providers in same metro | Materialized view, refreshed nightly |

---

## 4. New models required

| Model | Key fields | Purpose |
|---|---|---|
| `JobOffer` | `id`, `appointment_id?`, `provider_id`, `client_id`, `service_id`, `addons[]`, `pay_cents`, `duration_min`, `scheduled_at`, `address`, `surge_multiplier`, `created_at`, `responded_at`, `status`, `decline_reason` | Separates the offer/matching phase from the appointment FSM |
| `ProviderBlackoutDate` | `id`, `provider_id`, `start_date`, `end_date`, `reason` | Time-off windows |
| `ProviderServiceZone` | `id`, `provider_id`, `name`, `kind` (`primary|secondary|surcharge|excluded`), `radius_mi`, `center_h3`, `surcharge_cents` | Per-detailer service area |
| `Payout` | `id`, `provider_id`, `amount_cents`, `status`, `period_start`, `period_end`, `paid_at`, `stripe_transfer_id`, `kind` (`weekly|instant`) | Payout history |
| `PayoutSettings` | `provider_id`, `auto_payout_enabled`, `auto_payout_day`, `instant_fee_cents`, `default_method_id` | Per-provider payout config |
| `PayoutMethod` | `id`, `provider_id`, `kind`, `stripe_external_account_id`, `last4`, `bank_name`, `is_default` | Stripe Connect external accounts |
| `LedgerEntry` | `id`, `provider_id`, `kind` (`job_in|tip_in|payout_out|fee|credit|adjustment`), `amount_cents`, `label`, `appointment_id?`, `payout_id?`, `created_at` | Append-only financial ledger |
| `TaxForm` | `id`, `provider_id`, `tax_year`, `form_type`, `pdf_url`, `gross_cents`, `available_at` | Annual 1099s |
| `Specialty` | `id`, `name`, `slug` | Tag taxonomy (system-wide) |
| `ProviderSpecialty` | `provider_id`, `specialty_id` | M2M |
| `Verification` | `id`, `provider_id`, `kind`, `status`, `verifier`, `metadata_json`, `verified_at`, `expires_at` | Tracks each verification independently |
| `Badge` | `id`, `name`, `slug`, `emoji`, `criteria_json` | Achievement catalog |
| `ProviderBadge` | `provider_id`, `badge_id`, `earned_at` | M2M with timestamp |
| `PortfolioItem` | `id`, `provider_id`, `image_url`, `before_image_url?`, `caption`, `service_id?`, `display_order` | Profile gallery |
| `ReviewHighlight` | `id`, `provider_id`, `tag`, `mentions_count`, `sentiment`, `updated_at` | Auto-tagged keywords cloud |
| `ReviewAISummary` | `id`, `provider_id`, `summary_text`, `generated_at`, `model`, `review_count_at_generation` | Cached LLM summary |
| `Insight` | `id`, `provider_id`, `kind`, `title`, `body`, `action_url?`, `severity`, `created_at`, `dismissed_at?` | Insight feed |
| `PromoCode` | `id`, `provider_id`, `code`, `description`, `kind` (`percent|amount`), `value`, `max_uses`, `uses_count`, `applies_to_service_id?`, `starts_at`, `ends_at`, `is_active` | Detailer-issued discount codes |
| `PricingRule` | `id`, `provider_id`, `kind` (`travel_surcharge|weekend|same_day|loyalty|group`), `condition_json`, `value_cents_or_pct`, `is_active` | Per-provider pricing modifiers |
| `SupplyItem` | `id`, `provider_id`, `name`, `unit`, `stock`, `par`, `cost_cents`, `last_purchased_at`, `supplier` | Inventory tracking |
| `SupplyOrder` | `id`, `provider_id`, `items_json`, `total_cents`, `status`, `receipt_url`, `created_at` | Reorder history + receipt scans |
| `NotificationPref` | `provider_id`, `event`, `channels` (`push|sms|email`[]) | Notification routing |
| `AutoRule` | `id`, `provider_id`, `kind`, `params_json`, `is_active` | Job-handling automation |
| `DataExport` | `id`, `provider_id`, `requested_at`, `status`, `file_url`, `expires_at` | GDPR-style data exports |
| `SupportTicket` | `id`, `user_id`, `subject`, `body`, `category`, `status`, `priority`, `created_at`, `assigned_to?` | Help-center tickets |
| `OnlineStatus` | `provider_id`, `is_online`, `since`, `auto_offline_at?` | Sidebar accepting-jobs toggle |

---

## 5. Complete API endpoint list

### 5.1 Dashboard shell
- `GET /api/v1/dashboard/overview` — composite (me + kpis + earnings14d + route + incoming + insights + reviews). Reduces 7 round-trips to 1.
- `GET /api/v1/dashboard/search?q=` — cross-entity search.
- `GET /api/v1/notifications?cursor=&limit=` — paginated.
- `POST /api/v1/notifications/mark-read`.
- `PATCH /api/v1/me/online-status`.
- `GET /api/v1/insights?dismissed=false`.
- `POST /api/v1/insights/{id}/dismiss`.

### 5.2 Jobs
- `GET /api/v1/jobs?tab=&service=&search=&cursor=`.
- `GET /api/v1/jobs/incoming`.
- `POST /api/v1/jobs/offers/{id}/accept` → creates `Appointment`.
- `POST /api/v1/jobs/offers/{id}/decline` (with reason).
- `POST /api/v1/jobs/manual` (off-platform).
- `GET /api/v1/jobs/{id}` · `PATCH /api/v1/jobs/{id}/status` (uses existing FSM).
- `POST /api/v1/jobs/{id}/share-eta`.

### 5.3 Schedule
- `GET /api/v1/schedule/week?start=` · `GET /api/v1/schedule/month?year=&month=`.
- `GET/PATCH /api/v1/working-hours`.
- `GET/POST/DELETE /api/v1/blackout-dates`.
- `GET/POST/PATCH/DELETE /api/v1/service-zones`.
- `POST /api/v1/route/optimize`.

### 5.4 Earnings
- `GET /api/v1/earnings/summary` · `GET /api/v1/earnings/series?period=&granularity=` · `GET /api/v1/earnings/breakdown?by=service` · `GET /api/v1/earnings/ledger`.
- `GET /api/v1/payouts` · `POST /api/v1/payouts/cash-out`.
- `GET/PATCH /api/v1/payout-settings`.
- `GET/POST/DELETE /api/v1/payout-methods`.
- `GET /api/v1/tax-forms?year=` · `GET /api/v1/tax-forms/{id}/download`.
- `GET /api/v1/tax-estimate?year=`.

### 5.5 Customers
- `GET /api/v1/customers?filter=&sort=&cursor=`.
- `GET /api/v1/customers/{id}`.
- `GET /api/v1/customers/summary`.
- `GET /api/v1/customers/top-lifetime?limit=5`.
- `GET /api/v1/customers/winback-targets`.
- `POST /api/v1/campaigns/winback`.
- `POST /api/v1/customers/manual`.

### 5.6 Reviews
- `GET /api/v1/reviews?filter=`.
- `GET /api/v1/reviews/summary`.
- `GET /api/v1/reviews/highlights`.
- `GET /api/v1/reviews/ai-summary` · `POST /api/v1/reviews/ai-summary/refresh`.
- `POST /api/v1/reviews/{id}/reply`.
- `POST /api/v1/reviews/{id}/ai-suggest-reply`.
- `POST /api/v1/reviews/{id}/report`.

### 5.7 Services & pricing
- `GET/POST/PATCH/DELETE /api/v1/provider-services` (uses plan 09 base).
- `GET/POST/PATCH/DELETE /api/v1/promo-codes`.
- `GET/PATCH /api/v1/pricing-rules`.

### 5.8 Supplies
- `GET/POST/PATCH/DELETE /api/v1/supplies`.
- `GET /api/v1/supplies/summary`.
- `POST /api/v1/supplies/orders`.
- `POST /api/v1/supplies/scan-receipt` (multipart, OCR via Textract or Claude vision).
- `GET /api/v1/supplies/credits`.

### 5.9 Profile
- `GET/PATCH /api/v1/me/profile`.
- `POST /api/v1/me/photo`.
- `GET /api/v1/specialties` · `PATCH /api/v1/me/specialties`.
- `GET /api/v1/me/verifications` · `POST /api/v1/me/verifications/{kind}/start`.
- `GET /api/v1/me/badges`.
- `GET/POST/DELETE/PATCH /api/v1/me/portfolio`.

### 5.10 Settings
- `GET/PATCH /api/v1/me/notification-prefs`.
- `GET/PATCH /api/v1/me/auto-rules`.
- `GET /api/v1/me/sessions` (exists) · `DELETE /api/v1/me/sessions/{id}`.
- `POST /api/v1/me/2fa/setup` · `POST /api/v1/me/2fa/verify` · `DELETE /api/v1/me/2fa`.
- `POST/GET /api/v1/me/exports`.
- `GET/DELETE /api/v1/me/connected-apps`.
- `POST /api/v1/me/pause` · `POST /api/v1/me/resume`.
- `DELETE /api/v1/me` (soft-delete).

### 5.11 Help
- `GET /api/v1/support/articles?category=&q=`.
- `GET /api/v1/support/articles/{slug}`.
- `POST/GET /api/v1/support/tickets`.
- `GET /api/v1/support/status` (live-chat availability).

---

## 6. Execution phases

### Phase 1 — Read-only Core (Weeks 1–2)
Overview + Earnings tab fully functional. Jobs/Reviews/Customers read-only.

Backend: composite `/dashboard/overview`, earnings summary/series/breakdown/ledger, customers derived from appointments, reviews summary, insights stub.
Frontend: shell + sidebar + Overview view + Earnings view fully wired.

### Phase 2 — Write Actions + Jobs (Weeks 3–4)
Detailer can accept/decline offers, reply to reviews, manage services.

Backend: `JobOffer` + accept/decline split from existing matching; `ReviewReply`, `ReviewHighlight`, `ReviewAISummary` + Claude; promo codes + pricing rules.
Frontend: Jobs view, Reviews view (with AI suggest), Services & pricing view.

### Phase 3 — Schedule, Customers Detail, Profile (Weeks 5–6)
Backend: `ProviderBlackoutDate`, `ProviderServiceZone`; customer detail + win-back; specialties, verifications, badges, portfolio.
Frontend: Schedule view (week grid + working hours + zones); Today's route view; Customers detail + win-back UI; Profile view.

### Phase 4 — Financial Polish (Weeks 7–8)
Stripe Connect onboarding; `Payout`, `PayoutSettings`, `PayoutMethod`, `LedgerEntry`, `TaxForm`; tax estimate worker. Frontend: cash-out flow, auto-payout settings, tax forms download, tax set-aside tracker.

### Phase 5 — Supplies, Settings, Help (Weeks 9–10)
`SupplyItem`, `SupplyOrder` + receipt OCR; notification prefs, auto-rules, 2FA; support tickets + KB. Frontend: Supplies, Settings, Help views.

### Phase 6 — Advanced (Weeks 11+)
WebSocket real-time updates; manual job creation; connected apps (QuickBooks); AI insights worker; mobile-responsive provider dashboard.

---

## 7. Frontend routes

All under `web/dashboard/` (portal app (port 3001)), guarded by `active_role == detailer`.

| Route | Component |
|---|---|
| `/dashboard` | Redirect → `/dashboard/overview` |
| `/dashboard/overview` | `OverviewView` |
| `/dashboard/jobs` | `JobsView` (5 tabs) |
| `/dashboard/jobs/{id}` | `JobDetailView` |
| `/dashboard/route` | `TodaysRouteView` |
| `/dashboard/schedule` | `ScheduleView` |
| `/dashboard/earnings` | `EarningsView` |
| `/dashboard/customers` | `CustomersView` |
| `/dashboard/customers/{id}` | `CustomerDetailView` |
| `/dashboard/reviews` | `ReviewsView` |
| `/dashboard/services` | `ServicesView` |
| `/dashboard/supplies` | `SuppliesView` |
| `/dashboard/profile` | `ProfileView` |
| `/dashboard/settings` | `SettingsView` |
| `/dashboard/help` | `HelpView` |

---

## 8. Cross-cutting concerns

**Caching**: Composite endpoints + Redis 5-min TTL on KPIs + materialized views nightly. CDN signed URLs for portfolio/tax PDFs.

**Realtime**: `WS /ws/dashboard?token=<jwt>` pushes `job.offer.new`, `notification.created`, `review.posted`, `payout.completed`. 30s polling fallback.

**LLM**: Claude Haiku for review summaries (weekly batch) and AI-suggest replies (rate-limited 10/day/provider). Phase 6 insights also LLM-based.

**Permissions**: All `/api/v1/dashboard/**` require `active_role == detailer`. Admin can impersonate via `?as_provider={id}` (shadow mode — see plan 10).

**i18n**: EN-first in Phase 1; ES added in Phase 5 under `providerDashboard.*` namespace.

**Observability**: Every write writes to `audit_log`. P95 page load <1.2s, P95 API <200ms. Track per-view weekly engagement.

---

## 9. Verification

- [ ] All 8 KPI cards show real values matching SQL queries
- [ ] Earnings 14d chart renders from real appointment data
- [ ] Donut breakdown sums to 30d gross
- [ ] Ledger entries match `LedgerEntry` table exactly
- [ ] Accept-job creates `Appointment` and removes `JobOffer`
- [ ] Decline reason persists, visible to admin
- [ ] Schedule blackout dates remove available slots in client booking
- [ ] Working-hours edits reflect in client booking calendar within 1s
- [ ] Reply to review appears on rider-facing page
- [ ] AI summary refresh is idempotent and rate-limited
- [ ] Cash-out creates Stripe transfer + `LedgerEntry` of kind `payout_out`
- [ ] 1099-NEC download enforces ownership
- [ ] Customers list matches `count(DISTINCT client_id from completed appointments)`
- [ ] Online toggle removes provider from matching pool within 5s
- [ ] All 12 views keyboard-navigable
- [ ] Responsive at ≥1024px (desktop-first)
- [ ] All writes audit-logged
- [ ] Composite `/dashboard/overview` returns within 200ms P95

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| `JobOffer` split breaks existing matching | Feature flag `provider_offers_enabled`; ship Phase 2 behind flag |
| Earnings query slow on large datasets | Materialized view + Redis cache + diff-only after last cache point |
| Stripe Connect KYC variance per state | Defer to Phase 4; document per-state KYC in `infrastructure/stripe/` |
| LLM cost spike if every provider hits "AI suggest reply" 50×/day | Rate-limit 10/day/provider; cache 3 drafts per review 24h |
| Customer dashboard shares Vehicle/Address models | Plan 13 inherits shared models; this plan owns provider-side only |
| Service zones overlap global `service_zip_codes` from plan 16 | Provider zones are opt-in subsets of global coverage; validate at write |
| Notif prefs schema change breaks push delivery | Migration + grandfather defaults; emit `notification_pref.changed` |
| Sub-views (Profile/Settings/Help) ship at different velocities | Each is a separate route from day 1, no nested coupling |

---

## 11. Out of scope (other plans)

- Customer dashboard → plan 13
- Mechanic vertical dashboard → plan 14
- Marketing CMS (testimonials, FAQ, stats) → plan 15
- Coverage/ZIP service (global) → plan 16
- Waitlist system → plan 17
- Mobile RN provider home (uses existing `DetailerHomeScreen`)
- Multi-tenant agency mode
