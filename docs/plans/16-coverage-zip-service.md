# 16 — Coverage & ZIP Service

> **Status:** Planning
> **Priority:** Medium-High (blocks accurate booking flow)
> **Dependencies:** `infrastructure/h3/` (spatial indexing already exists for matching), `15-marketing-content-cms.md` (admin UI to manage zones)
> **Audit findings resolved:** N/A
> **Design source:** `web/portal/components/sections/Coverage.tsx` (currently hardcoded 5-ZIP allowlist), `dash-schedule.jsx` service-zones table (per-provider zones), `customer-a.jsx` coverage check on hero

---

## 1. Objective

Replace the **hardcoded ZIP allowlist** in `web/portal/components/sections/Coverage.tsx` and the **hardcoded "Fort Wayne, Aboite, Huntertown, ..." string** scattered across pages with a real **coverage service**.

The system must answer two questions:
1. **"Do you serve this ZIP / address?"** (public — landing page check, customer booking pre-check)
2. **"Which providers serve this ZIP?"** (internal — matching engine input)

It must also support:
- Admin defining service areas (active, planned, surcharge, excluded)
- Per-provider zone overrides (some providers serve broader, some narrower)
- Future cities (Fort Wayne first → multiple metros over time)
- ETA estimation per zone (some zones have longer dispatch times)

---

## 2. Current state

### 2.1 Code references
| Where | What |
|---|---|
| `web/portal/components/sections/Coverage.tsx` | Hardcoded array `["46802","46804","46805","46807","46815"]` |
| `web/portal/messages/en.json::coverage.areas[]` | Hardcoded 6 neighborhoods |
| `dash-schedule.jsx::ViewSchedule` | Hardcoded per-provider zones (Aboite, Lakeside, Northwood, Glenwood, New Haven, Huntertown) with surcharge/active states |
| `backend/infrastructure/h3/` | Hex-based spatial indexing for matching (exists, used by matching engine) |
| `backend/app/db/seed.py` | May seed Fort Wayne lat/lng on first run — verify |

### 2.2 What's missing
- **No `service_zip_codes` table** — coverage is implicit (matching tries all providers, returns no-results if none in range).
- **No public coverage endpoint** for the marketing page.
- **No admin tool** to add/remove service areas.
- **No surcharge tiers** (the design shows "+$15 surcharge" zones).
- **No expansion planning** ("coming Q3 to City X" sign-ups).

---

## 3. Architecture

### 3.1 Two-level hierarchy

**Level 1 — Platform coverage** (admin-managed): defines which metros/cities/zones the platform operates in.

**Level 2 — Provider zones** (per-provider, opt-in subsets of L1): each provider declares which of the platform's active zones they serve.

A request to "do you serve ZIP X?" first checks L1 → if not, returns `not_covered`. If yes, checks if any provider in L2 covers it → returns coverage status with expected ETA.

### 3.2 Spatial representation
- **ZIP-based**: fast lookup, common user input.
- **H3-cell-based**: precise lat/lng-to-coverage check, used by matching.
- **Polygon-based** (optional): for irregular metro boundaries, future.

Each `ServiceArea` stores all three so the API can answer different question shapes.

---

## 4. New models

| Model | Key fields | Purpose |
|---|---|---|
| `Metro` | `id`, `slug` ("fort-wayne-in"), `name`, `state`, `country`, `center_lat`, `center_lng`, `timezone`, `is_active`, `launch_at?`, `display_order` | Top-level expansion unit |
| `ServiceArea` | `id`, `metro_id`, `name` ("Aboite"), `slug`, `kind` (`active|planned|surcharge|excluded`), `surcharge_cents`, `eta_minutes` (median dispatch time), `h3_cells[]` (resolution 7-8), `zip_codes[]`, `display_order`, `is_active` | Sub-metro zone |
| `ServiceAreaPolygon` | `id`, `service_area_id`, `geojson_polygon` | Optional precise boundary |
| `WaitlistedZip` | `id`, `zip`, `email?`, `requested_at`, `notified_at?`, `service_area_id?` (assigned when zone is launched) | Capture interest from unsupported ZIPs |
| `ProviderServiceArea` | `provider_id`, `service_area_id`, `surcharge_override_cents?`, `is_active`, `created_at` | Per-provider zone opt-in (already in plan 11 as `ProviderServiceZone`; this model harmonizes naming) |

---

## 5. API endpoints

### 5.1 Public (marketing + booking)
- `GET /api/v1/coverage/zip/{zip}` →
  ```json
  {
    "covered": true,
    "kind": "active",
    "service_area": { "id", "name": "Aboite", "metro": "Fort Wayne, IN" },
    "eta_minutes_median": 35,
    "surcharge_cents": 0,
    "providers_count": 12
  }
  ```
  Or:
  ```json
  {
    "covered": false,
    "kind": "not_covered",
    "nearest_active_area": { "name": "Aboite", "distance_mi": 12 },
    "waitlist_available": true
  }
  ```
- `GET /api/v1/coverage/areas?metro=` — list all active areas (for the coverage map).
- `GET /api/v1/coverage/metros` — list all metros.
- `POST /api/v1/coverage/notify-me` — capture email for unsupported ZIP → creates `WaitlistedZip`.

### 5.2 Booking-flow integration
- `POST /api/v1/availability/check` (existing) now accepts `address` → returns coverage status + slots in one call.

### 5.3 Admin
- `GET/POST/PATCH/DELETE /api/v1/admin/metros`.
- `GET/POST/PATCH/DELETE /api/v1/admin/service-areas` (incl. `kind`, `surcharge_cents`, `zip_codes[]`).
- `POST /api/v1/admin/service-areas/{id}/import-zips` — bulk CSV upload.
- `GET /api/v1/admin/waitlisted-zips?metro_id=&since=` — analytics on demand outside coverage.
- `POST /api/v1/admin/waitlisted-zips/{id}/notify` — email customer that their ZIP is now covered.

### 5.4 Provider-facing (from plan 11 §5.3, harmonized here)
- `GET /api/v1/me/service-areas` — provider's opted-in areas.
- `POST /api/v1/me/service-areas` — opt in to a platform area.
- `PATCH /api/v1/me/service-areas/{id}` — set surcharge override.
- `DELETE /api/v1/me/service-areas/{id}` — opt out.

---

## 6. ZIP → area resolution algorithm

```
def resolve_coverage(zip: str) -> CoverageResult:
    # 1. Direct ZIP match
    area = ServiceArea.find_by_zip(zip)  # active or planned only
    if not area:
        # 2. Geocode the ZIP centroid, check H3 cell
        lat, lng = geocode_zip(zip)
        if not lat:
            return CoverageResult(covered=False, kind="unknown")
        cell = h3_to_index(lat, lng, resolution=7)
        area = ServiceArea.find_by_h3_cell(cell)
    if not area:
        # 3. No area → find nearest active
        nearest = ServiceArea.nearest_active(lat, lng)
        return CoverageResult(
            covered=False,
            kind="not_covered",
            nearest_active_area=nearest,
            waitlist_available=True,
        )
    # 4. Found area — compute ETA + provider count
    provider_count = ProviderServiceArea.count_active(area.id)
    eta = compute_eta_median(area, provider_count)
    return CoverageResult(
        covered=(area.kind in ("active", "surcharge")),
        kind=area.kind,
        service_area=area,
        eta_minutes_median=eta,
        surcharge_cents=area.surcharge_cents,
        providers_count=provider_count,
    )
```

ZIP-to-coordinates is cached at app boot from a static USZIP dataset; refreshed quarterly.

---

## 7. Surcharge handling

When `area.kind == "surcharge"`:
- Booking flow shows the surcharge upfront before confirming.
- `appointment.surcharge_cents` field records the applied charge.
- Provider sees the surcharge in their net pay (depending on platform-fee policy).

When `area.kind == "excluded"`:
- ZIP appears "not_covered" to customer.
- Internal admin can still see the area for analytics.

---

## 8. Marketing-side integration

After this plan ships:

1. **`Coverage.tsx`** swaps hardcoded ZIPs for:
   ```ts
   const res = await fetch(`/api/v1/coverage/zip/${zip}`)
   ```
2. **`coverage.areas[]`** in i18n is removed; replaced with `GET /api/v1/coverage/areas?metro=fort-wayne-in` rendered server-side.
3. **Coverage map SVG** dynamically positions pins from `service_area.center_{lat,lng}`.
4. **Waitlist capture** on "not covered" uses the existing waitlist system (plan 17).

---

## 9. Execution phases

### Phase 1 — Core models + admin (Weeks 1–2)
- `Metro`, `ServiceArea`, `WaitlistedZip` models + migrations.
- Seed Fort Wayne metro + 6 areas from current hardcoded list.
- Admin endpoints + UI.
- Public `GET /coverage/zip/{zip}` + `GET /coverage/areas` endpoints.

### Phase 2 — Marketing integration (Week 3)
- Refactor `Coverage.tsx` to use real API.
- Move `coverage.areas` out of i18n into CMS-driven via plan 15.
- Add "notify me" form on unsupported ZIPs.

### Phase 3 — Provider opt-in (Week 4)
- Provider dashboard sub-view: "Service Areas" (list of platform areas, opt in/out, surcharge override).
- Wire into matching engine (only providers in the area pool can match).

### Phase 4 — Spatial precision (Week 5)
- H3 cell indexing for sub-ZIP precision.
- Polygon boundary support for irregular metros.
- ETA computation from historical dispatch data.

### Phase 5 — Expansion automation (Week 6+)
- Admin "Launch new metro" workflow: define name, center, polygon, target launch date.
- Auto-notify waitlisted ZIPs when their area becomes active.
- Public "expansion roadmap" page showing planned areas.

---

## 10. Frontend changes

| File | Change |
|---|---|
| `web/portal/components/sections/Coverage.tsx` | Replace hardcoded array with API call; show real coverage + ETA |
| `web/portal/messages/{en,es}.json::coverage.areas[]` | Remove; fetched at request time |
| `web/portal/app/[locale]/(marketing)/page.tsx` | If using SSR fetch, add `coverage` data to props |
| `frontend/src/screens/BookingScreen.tsx` | Pre-check coverage before allowing booking |
| `frontend/src/screens/AddressFormScreen.tsx` | Inline coverage check on ZIP change |
| `web/admin/coverage/page.tsx` | New admin UI |
| `web/dashboard/service-areas/page.tsx` | Provider opt-in page |

---

## 11. Verification

- [ ] `GET /coverage/zip/46802` returns `covered: true, kind: "active"`
- [ ] `GET /coverage/zip/90210` returns `covered: false` + nearest area suggestion
- [ ] Surcharge zone reflects `surcharge_cents` correctly in booking flow
- [ ] Excluded zone shows "not covered" to customer
- [ ] Waitlist capture creates `WaitlistedZip` row
- [ ] Admin can create a new area with ZIPs + see it on the public map
- [ ] Provider opts into an area → matching engine includes them in pool
- [ ] ETA computation reflects actual recent dispatch times (or default if no data)
- [ ] Coverage check responds <50ms P95 (heavily cached)
- [ ] Marketing site falls back to "Fort Wayne metro" generic text if API fails

---

## 12. Risks

| Risk | Mitigation |
|---|---|
| ZIP centroid is wrong (multi-county ZIPs) | Use polygon boundary when high precision matters; flag border ZIPs |
| H3 resolution mismatch between coverage and matching | Standardize on res 7 (~5 km²) for both |
| Stale ZIP geocode data | Quarterly refresh job from USZIP/USPS |
| Customer in excluded zone uses VPN/manual address override | Booking flow re-validates server-side; cancel + refund if mismatch |
| Provider opts in to a planned (not-yet-launched) area | Validation: cannot opt in to non-active area |
| Waitlist email floods on city expansion | Batch send + opt-in confirmation pattern |
| Surcharge transparency / regulatory variance per state | Show surcharge breakdown before checkout; per-state config |

---

## 13. Out of scope

- Real-time map rendering with provider pins (use static map with pins for now)
- Live "providers near you" socket
- Route-time estimation (Google Maps API integration deferred)
- International expansion (US-only assumptions: ZIP format, state codes)
