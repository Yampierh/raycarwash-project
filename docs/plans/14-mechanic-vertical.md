# 14 — Mechanic Vertical (Backend Build-out)

> **Status:** Planning · pre-launch (Q4 2026 beta target)
> **Priority:** Medium (after detailing vertical hardening)
> **Dependencies:** `09-provider-services-integration.md`, `11-provider-dashboard.md`, `15-marketing-content-cms.md`, `17-waitlist-system.md`
> **Audit findings resolved:** N/A
> **Design source:** `raycarwash/project/Mechanic Page.html` + `raycarwash/project/src/mechanic.jsx` + already-shipped marketing route `web/portal/app/[locale]/(marketing)/mechanic/page.tsx`

---

## 1. Objective

Add **mobile mechanic** as a second service vertical alongside detailing. Customers book oil changes, brake jobs, diagnostics, etc. — performed where the car is parked. Providers are ASE-certified mechanics, not detailers; they share the same provider FSM and dashboard surface but operate over a different services catalog and verification stack.

The marketing page already ships at `/mechanic` as a coming-soon waitlist. This plan covers the backend to turn that page into a live product.

---

## 2. Hardcoded data inventory (from `mechanic.jsx`)

### 2.1 Eight launch services
```
oil_change       · $65  · 30m · Full-synthetic + filter
brake_pads       · $280 · 90m · Front or rear axle, OEM-equivalent
battery          · $180 · 20m · AGM or lead-acid, includes core return
diagnostics      · $75  · 30m · Full OBD-II read + app report
tire_rotation    · $35  · 25m · All four, torque-spec'd
wiper_blades     · $35  · 10m · Pair, installed
filters          · $55  · 20m · Air + cabin filters
spark_plugs      · $220 · 60m · Full set, iridium or platinum
```

### 2.2 Mechanic-specific concepts (not in detailing)
- **Parts**: separately tracked from labor. Customer sees flat parts-plus-labor quote; backend tracks both.
- **OBD-II diagnostic reports**: structured data (error codes, severity).
- **Warranty**: 12-month / 12,000-mile parts-and-labor.
- **Referrals out**: if job requires a shop (transmission, alignment), diagnostic fee credits toward shop.
- **Service van inventory**: parts pre-pulled per appointment based on vehicle Y/M/M.
- **Founding mechanic perks**: reduced platform fee for first 6 months.

### 2.3 Provider requirements (different from detailers)
- ASE certification (any specialty)
- Own service van + portable lift
- Mobile or shop experience
- Commercial liability insurance

### 2.4 Workflow
- Booking flow identical to detailing in design ("Same as detailing. Different toolkit.")
- Appointment timeline adds: parts pre-pull confirmation, diagnostic step (if applicable), inspection-pass step before payment release.

---

## 3. Backend gap analysis

### 3.1 Service catalog
| Need | Current state | Gap |
|---|---|---|
| Multiple service categories (detailing, mechanic) | `services` table is flat | Add `service_categories` table + `category_id` FK on services |
| Parts-plus-labor pricing | Single `price_cents` | Add `parts_cents`, `labor_cents`, `default_parts_json` |
| Vehicle-aware pricing | Static price | Add `pricing_rules.condition_json` already in plan 11 — extend to honor Y/M/M |
| Service requires diagnostic step | Single-step | Add `service.steps_json` enum array (e.g. `[diagnose, parts_pull, work, inspect, pay]`) |

### 3.2 Provider domain
- Mechanic providers share `users + provider_profiles` schema but have different `verification.kind` requirements.
- New `Verification.kind` values: `ase_cert`, `service_van`, `commercial_liability`.
- New `Specialty` taxonomy entries: `engine`, `brakes`, `electrical`, `tires`, `hvac`, etc.
- Provider `service_categories[]` indicates which verticals they serve.

### 3.3 Appointment
- Existing FSM is `pending → confirmed → arrived → in_progress → completed` (+cancellations).
- Mechanic vertical needs extension: `pending → confirmed → arrived → diagnosing → quote_pending → quote_approved → in_progress → inspection → completed`.
- Add `appointment.diagnostic_report_json` and `appointment.parts_invoice_json`.
- Add a "needs shop referral" terminal state.

### 3.4 Inventory
- Per-mechanic parts inventory tied to vehicles served (echoes Provider Dashboard supplies but parts-specific).
- Pre-pull list generated when appointment is confirmed.

### 3.5 Warranty tracking
- `AppointmentWarranty` model: `appointment_id`, `parts_warranty_until`, `labor_warranty_until`, `voided_at?`.
- Customer can file a warranty claim → creates linked re-appointment at $0.

---

## 4. New models required

| Model | Key fields | Purpose |
|---|---|---|
| `ServiceCategory` | `id`, `slug` (`detailing|mechanic`), `name`, `display_order`, `is_active` | Vertical separation |
| `ServicePart` | `id`, `service_id`, `name`, `unit_cost_cents`, `markup_pct`, `vehicle_filter_json` (Y/M/M conditions) | Parts catalog tied to services |
| `ASECertification` | `id`, `provider_id`, `specialty_codes[]` (A1-A9 etc.), `cert_number`, `expires_at`, `verified_at` | ASE cert tracking |
| `DiagnosticReport` | `id`, `appointment_id`, `obd_codes_json` (list of `{code, description, severity}`), `summary`, `recommendations_json`, `pdf_url`, `created_at` | OBD-II reports |
| `PartsInvoice` | `id`, `appointment_id`, `parts_json` (list of `{name, qty, unit_cost, total}`), `parts_total_cents`, `labor_cents`, `tax_cents`, `total_cents` | Itemized parts-plus-labor |
| `AppointmentWarranty` | `id`, `appointment_id`, `parts_warranty_until`, `labor_warranty_until`, `mileage_limit?`, `voided_at?`, `void_reason?` | Warranty period |
| `WarrantyClaim` | `id`, `original_appointment_id`, `claim_reason`, `status`, `re_appointment_id?`, `outcome` (`approved|denied|partial`), `created_at` | Warranty redemption |
| `ShopReferral` | `id`, `appointment_id`, `recommended_shops_json`, `diagnostic_fee_credit_cents`, `accepted_shop_id?` | When job requires a shop |
| `MechanicVanInventory` | `id`, `provider_id`, `vehicle_id?` (or static-cargo), `parts_json`, `updated_at` | Per-van stock snapshot |
| `MechanicSpecialty` | reuses `Specialty` taxonomy with `category="mechanic"` field | — |

---

## 5. API endpoints

### 5.1 Customer-facing
- `GET /api/v1/services?category=mechanic` — services list scoped to vertical.
- `POST /api/v1/me/appointments` (existing) — `category` parameter routes through mechanic matching.
- `GET /api/v1/me/appointments/{id}/diagnostic-report` — view OBD-II report.
- `POST /api/v1/me/appointments/{id}/quote-approval` — approve revised quote after diagnosis.
- `POST /api/v1/me/appointments/{id}/quote-decline` — decline, pay diagnostic fee only.
- `POST /api/v1/me/warranty-claims` — file claim.
- `GET /api/v1/me/warranty-claims` — list active warranties + claim history.

### 5.2 Provider-facing (extends provider dashboard)
- `GET /api/v1/dashboard/jobs?category=mechanic` — filter by vertical.
- `POST /api/v1/jobs/{id}/diagnostic-report` — submit OBD reading + recommendations.
- `POST /api/v1/jobs/{id}/parts-invoice` — itemize parts.
- `POST /api/v1/jobs/{id}/inspect-pass` — mark inspection complete (gates payment release).
- `POST /api/v1/jobs/{id}/shop-referral` — escalate to a shop.
- `GET/PATCH /api/v1/me/van-inventory`.
- `POST /api/v1/me/ase-certification` — submit ASE for verification.

### 5.3 Admin
- `GET/PATCH /api/v1/admin/service-categories`.
- `GET/POST/PATCH /api/v1/admin/parts-catalog`.
- `GET /api/v1/admin/mechanic-applications` — review founding mechanic applications.
- `PATCH /api/v1/admin/providers/{id}/categories` — assign vertical(s) to a provider.

---

## 6. Booking flow differences

| Step | Detailing | Mechanic |
|---|---|---|
| 1. Service select | Browse list | Browse list (now with category filter) |
| 2. Vehicle | Pick saved vehicle | Same — but Y/M/M now triggers parts pre-pull preview |
| 3. Time | Available slots | Same |
| 4. Quote | Final flat | **Initial quote** (parts pre-pulled at standard); can change after diagnosis |
| 5. Auth payment | Hold via Stripe | Same |
| 6. Detailer dispatch | Match nearest verified | Match nearest **ASE-certified** in specialty |
| 7. Arrival | Service starts | **Diagnostic step first** if applicable |
| 8. Quote revision | N/A | If diagnostic finds extra work → push revised quote → client approves/declines |
| 9. Work | Single phase | Phased (diagnose → parts → work → inspect) |
| 10. Inspection | Visual only | Test drive / OBD re-scan to confirm fix |
| 11. Payment release | On `completed` | On `inspection_pass` |
| 12. Warranty | None | 12-mo / 12,000-mi parts+labor written to `AppointmentWarranty` |

---

## 7. Execution phases

### Phase 1 — Catalog Foundations (Weeks 1–2)
- `ServiceCategory` model + migration
- `ServicePart` catalog
- Extend `Service` with `category_id`, `steps_json`, `requires_diagnostic`
- Admin endpoints to seed mechanic services + parts catalog
- Marketing page `/mechanic` switches from hardcoded JSON to `GET /api/v1/services?category=mechanic`

### Phase 2 — Provider Onboarding (Weeks 3–5)
- `ASECertification` model + verification flow (manual admin verification initially; later integrate ASE NDA API)
- Update detailer onboarding to support mechanic vertical (different requirements)
- Founding-mechanic offer flow: admin grants reduced fee for 6 months via `pricing_rules` of kind `platform_fee_override` (already in plan 11)
- Provider dashboard sidebar shows mechanic-specific tabs (parts inventory, diagnostic library, warranty claims)

### Phase 3 — Booking Flow (Weeks 6–8)
- Extend appointment FSM with `diagnosing`, `quote_pending`, `quote_approved`, `inspection`
- `DiagnosticReport` + `PartsInvoice` endpoints
- Quote revision flow in client mobile app + web dashboard
- Inspection step + payment release gating

### Phase 4 — Warranty & Claims (Weeks 9–10)
- `AppointmentWarranty` + `WarrantyClaim`
- Customer dashboard "Warranties" sub-view
- Claim handling workflow

### Phase 5 — Shop Referrals (Weeks 11+)
- `ShopReferral` model
- Partner shop directory (out of scope for V1; admin-curated CSV initially)
- Diagnostic fee credit logic

---

## 8. Frontend routes (added/modified)

| Route | Notes |
|---|---|
| `marketing/mechanic/page.tsx` | Already exists; switch services source from i18n hardcoded to API |
| `frontend/src/screens/MechanicBookingScreen.tsx` | New screen variant of existing `BookingScreen`, with category=mechanic prefilled |
| `marketing/(app)/client/dashboard/warranties/page.tsx` | Customer dashboard sub-view |
| `web/dashboard/parts-inventory/page.tsx` | Provider dashboard sub-view (mechanic-only) |
| `web/dashboard/diagnostic-library/page.tsx` | Common OBD codes + recommended fixes |

---

## 9. Marketing content currently hardcoded → should be admin-controlled

The 8 launch services, the rollout phases (Q4 2026 beta, etc.), the founding-mechanic perks (reduced fee, equipment financing), and the FAQ items should all be admin-tunable so the page can evolve without redeploying. This is owned by **plan 15 (Marketing CMS)**.

Specifically, the `marketing/messages/en.json::mechanicPage` section should be split into:
- **Static i18n keys** (page labels, section titles)
- **CMS-driven content** (services list, rollout phases, perks list, FAQ items)

---

## 10. Verification

- [ ] `GET /services?category=mechanic` returns the 8 launch services
- [ ] ASE-certified provider can be onboarded end-to-end
- [ ] Booking with `category=mechanic` triggers mechanic matching pool
- [ ] Diagnostic report PDF generates and is downloadable by customer
- [ ] Quote revision flow blocks work start until customer approves
- [ ] Inspection step gates payment release
- [ ] Warranty automatically attached to completed mechanic appointments
- [ ] Warranty claim creates a $0 re-appointment
- [ ] Shop referral credits diagnostic fee back to customer
- [ ] Founding-mechanic platform fee override applies for 6 months from activation
- [ ] Mechanic provider sidebar shows parts inventory + warranty claims
- [ ] Customer dashboard shows active warranties

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| ASE cert verification is manual initially | Admin queue with SLA; integrate ASE NDA API in Phase 2.5 |
| Parts pricing varies wildly by region | Per-mechanic parts overrides; suggest national defaults |
| OBD-II readings require hardware integration | Phase 1 = manual entry by mechanic; Phase 2 = Bluetooth OBD adapter integration |
| Quote-revision UX confuses customers (price changes after booking) | Strong UX cues + cap revision pct (e.g. ≤30% above original) without explicit re-auth |
| Warranty fraud (customer claims work failed when it didn't) | Mechanic uploads inspection photos; admin arbitration |
| Diagnostic fee credit if referred to shop — accounting complexity | Track in `LedgerEntry` of kind `credit`; expire after 90 days |
| Founding-mechanic offer creates pricing inconsistency | Time-boxed via `pricing_rules.starts_at` / `ends_at`; auto-expire |
| Mechanic vertical splits matching pool — could starve detailing | Independent pools; cross-vertical providers possible but rare |

---

## 12. Out of scope (deferred)

- ICE engine specifics vs EV (handled implicitly via Y/M/M filter)
- Tire sales (only rotation in launch services)
- Fleet/commercial accounts
- Mobile body work / paintless dent repair (separate future vertical)
- Roadside assistance (different SLA, separate vertical)
- Recall lookup integration with NHTSA
