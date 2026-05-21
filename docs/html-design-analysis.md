# HTML Design Analysis — raycarwash/project/

> **Purpose:** Feature-by-feature mapping of each HTML page's design against backend/existing code status.
> **Source:** `raycarwash/project/` — 6 HTML wrappers + ~25 JSX components + 6 CSS files
> **Generated:** 2026-05-21

---

## 1. Landing Page

**File:** `raycarwash/project/Landing Page.html`
**JSX sources:** `app.jsx`, `sections-a.jsx`, `sections-b.jsx`, `icons.jsx`, `phone-mock.jsx`
**CSS:** `styles.css`
**Existing route:** `/[locale]/(marketing)/page.tsx`

### Sections

| Section | Component | Design Features | Existing in `marketing/` | Gaps |
|---------|-----------|----------------|--------------------------|------|
| **Navbar** | `Navbar` | Audience toggle (Riders/Detailers), links to sub-pages, Log in / Get the app CTAs, badge for "new" mechanic link | `Navbar.tsx` exists but simpler | Full redesign needed — audience toggle is new, link structure differs |
| **Hero** | `Hero` | Full-viewport gradient, audience-aware headline/subtitle, phone mockup with animated steps, stats bar (2,400+ details, 22 min ETA, 4.9★), CTA buttons per audience | `Hero.tsx` exists but basic | Full redesign — stats bar, phone mockup, animated steps, audience toggle all new |
| **Trust Strip** | `TrustStrip` | 3 columns: Verified detailers, Insured service, Satisfaction guarantee | Not in existing site | New component needed |
| **How It Works** | `HowItWorks` | 4 steps with icons, audience-aware (client steps vs detailer steps) | `HowItWorks.tsx` exists | Redesign to match prototype styling; audience-aware content is new |
| **Services** | `Services` | 3 pricing cards (Exterior $49, Full $149, Interior $89) with features list, "Most popular" badge | `Services.tsx` exists | Redesign to match card styling |
| **Coverage** | `Coverage` | SVG map of Fort Wayne neighborhoods + ZIP checker input | Not in existing site | New component; SVG map is design-only placeholder |
| **For Detailers** | `ForDetailersSplit` | 4 benefit cards (schedule, payouts, verified clients, tools), earnings stats card with bar, CTA | `ForDetailers.tsx` exists but different | Redesign with earnings stats card is new |
| **Testimonials** | `Testimonials` | Grid of testimonial cards with stars, rating summary header (4.9★) | `Testimonials.tsx` exists | Redesign with wall/masonry layout |
| **FAQ** | `FAQ` | Accordion with 8 items | `FAQ.tsx` exists | Content differs; structure similar |
| **Final CTA** | `FinalCTA` | Audience-aware CTA (Download app / Apply now) with photo mosaic | `ContactCTA.tsx` exists | Redesign with full card layout |
| **Footer** | `Footer` | 4-column: brand + stores + Product/Company/Legal links | `Footer.tsx` exists | Redesign needed; new store buttons |

### Backend Integration Points

| Feature | Backend Status |
|---------|---------------|
| Stats (2,400+ details, 22 min ETA) | Marketing-only mock data |
| Pricing ($49–$149) | ✅ Services catalog endpoint exists |
| Coverage (ZIP check) | ❌ No ZIP/coverage endpoint |
| CTA → signup | ✅ Auth endpoints exist |
| CTA → booking (mobile) | App store links only |

---

## 2. Customer (Riders) Page

**File:** `raycarwash/project/Customer Page.html`
**JSX sources:** `customer-app.jsx`, `customer-a.jsx`, `customer-b.jsx`, `sections-b.jsx`, `icons.jsx`, `phone-mock.jsx`
**CSS:** `styles.css`, `customer.css`
**Existing route:** `/[locale]/(marketing)/riders/page.tsx`

### Sections

| Section | Component | Design Features | Existing | Gaps |
|---------|-----------|----------------|----------|------|
| **Navbar** | `CustNavbar` | Brand with "/ riders" sub-label, links (How, Services, Safety, Reviews, FAQ), sub-page links (Detailers, Mechanic new) | Navbar exists but simple | Full redesign |
| **Hero** | `CustHero` | Two phone side-by-side (booking flow), quick info (Book in 90s, Insured, No surprises), rating bar (4.9★, 1,240+ reviews, 22 min ETA), app store CTAs | Basic hero exists | Full redesign — phone mockups, quick stats, dual hero |
| **Booking Journey** | `BookingJourney` | 4-step interactive tabs (Pick service → Choose time → Watch arrive → Pay & rate), phone mockup per step, tags | Not in existing site | New component |
| **Services Compare** | `ServicesCompare` | Comparison table: Exterior ($49), Interior ($89), Full Detail ($149) with feature checkmarks + add-ons grid (pet hair $25, headlights $40, etc.) | `Services` section exists but simpler | Full redesign — table format, add-ons grid |
| **Trust/Safety** | `TrustSafety` | 4 pillars (Identity verified, Background checked, Insured, Documented) with stats + dispute card (94% resolved in 24hr) | Not in existing | New component |
| **Reviews** | `ReviewsWall` | Masonry-style review cards with varying sizes (8 reviews, 5★ each) | `Testimonials` exists | Redesign with full wall layout |
| **FAQ** | `CustFAQ` | 8 items specific to riders | FAQ exists | Content updated |
| **CTA** | `CustCTA` | App store buttons + QR code | `ContactCTA` exists | Redesign with QR card |

### Backend Integration Points

| Feature | Backend Status |
|---------|---------------|
| Pricing table ($49–$149) | ✅ Services catalog + variants |
| Add-ons list | ✅ Addons endpoint exists |
| Reviews (1,240+ count) | ❌ Reviews exist but no aggregate stats endpoint |
| Trust/safety data | Marketing copy — no live data needed |
| Booking journey | ✅ Booking flow fully implemented |

---

## 3. Detailers Page

**File:** `raycarwash/project/Detailers Page.html`
**JSX sources:** `detailers-app.jsx`, `detailers-a.jsx`, `detailers-b.jsx`, `sections-b.jsx`, `icons.jsx`
**CSS:** `styles.css`, `detailers.css`
**Existing route:** `/[locale]/(marketing)/detailers/page.tsx`

### Sections

| Section | Component | Design Features | Existing | Gaps |
|---------|-----------|----------------|----------|------|
| **Navbar** | `DetNavbar` | Brand with "/ detailers" sub-label, links (Earnings, A Week, Tools, Requirements, FAQ), sub-page links, "Apply to detail" CTA | Navbar exists but simple | Full redesign |
| **Hero** | `DetHero` | Payout card with earnings ($2,148.50/wk, +18%), mini-bar chart, orbit chips (4.9★, 312 jobs, 98% on-time), trust strip (4 min app, 48 hr decision, same-day payouts) | Basic hero exists | Full redesign — payout card, earnings visualization |
| **Earnings Calculator** | `EarningsCalc` | Interactive calculator with sliders (jobs/wk, avg ticket, days worked), dynamically calculates weekly/monthly/yearly net, benchmarks vs median/top quartile | Not in existing | New interactive component |
| **Week in Life** | `WeekInLife` | Full week schedule grid showing real detailer's jobs per day, totals per day, weekly total ($1,143, 13 jobs) | Not in existing | New component |
| **Tools** | `Tools` | 3 phone mockups: Smart dispatcher, Route/day planner, Before/after capture, dark section | Not in existing | New component; marketing-only |
| **Requirements** | `Requirements` | Checklist (6 items) + 4-step guide (Apply → Verify → Setup → Earn) | Not in existing | New component |
| **Testimonials** | `DetTestimonials` | Detailer-specific testimonials (Marcus, Trey, Jamal) with job stats | Exists as general testimonials | New content, same pattern |
| **FAQ** | `DetFAQ` | 7 items specific to detailers | FAQ exists | Content updated |
| **CTA** | `DetCTA` | Application preview card showing 4-step progress (62% complete) | `ContactCTA` exists | Full redesign with progress preview |

### Backend Integration Points

| Feature | Backend Status |
|---------|---------------|
| Earnings data | ❌ Marketing-only mock data (no live earnings calculator) |
| Application flow | ✅ Registration + onboarding endpoints exist |
| Payout data | ❌ No public earnings stats |
| Tools (dispatcher, planner, photos) | Marketing-only mockups |
| Requirements | Marketing copy |

---

## 4. Mechanic Page (NEW)

**File:** `raycarwash/project/Mechanic Page.html`
**JSX sources:** `mechanic.jsx`, `sections-b.jsx`, `icons.jsx`
**CSS:** `styles.css`, `mechanic.css`
**Existing route:** ❌ NEW — `/[locale]/(marketing)/mechanic/page.tsx`

### Sections

| Section | Component | Design Features | Existing | Gaps |
|---------|-----------|----------------|----------|------|
| **Navbar** | `MechNavbar` | Brand with "/ mechanic" sub-label, links (Services, How, Waitlist, FAQ) | N/A | New component |
| **Hero** | `MechHero` | Badge (Q4 2026 · Beta), waitlist form with live counter (347+ people), check bullets, toolbox SVG art | N/A | New component; waitlist form is design-only |
| **Services** | `MechServices` | 8 service cards: Oil change ($65), Brakes ($280), Battery ($180), Diagnostics ($75), Tire rotation ($35), Wipers ($35), Filters ($55), Spark plugs ($220) with durations | N/A | New component; services are marketing reference |
| **How It Works** | `MechHow` | 4 steps (Book → Pick window → Show up loaded → Watch or walk away) | N/A | New component |
| **For Mechanics CTA** | `MechProviderCTA` | Recruiting section for mechanics with requirements (ASE cert, van, experience, insurance) + founding perks card (0% fee, $1,200/wk min, 12/20 spots) | N/A | New component |
| **FAQ** | `MechFAQ` | 6 items specific to mechanic vertical | N/A | New component |
| **CTA** | `MechCTA` | Waitlist + rollout plan timeline (Q2 2026 → Q3 2027) | N/A | New component |

### Backend Integration Points

| Feature | Backend Status |
|---------|---------------|
| Waitlist signup | ❌ No waitlist endpoint |
| Service listings | ✅ Mechanic service catalog exists in backend |
| Mechanic recruitment | ❌ No mechanic-specific registration flow |
| Rollout timeline | Marketing copy |

---

## 5. Customer Dashboard

**File:** `raycarwash/project/Customer Dashboard.html`
**JSX sources:** `cdash-icons.jsx`, `cdash-data.jsx`, `cdash-shell.jsx`, `cdash-home.jsx`, `cdash-bookings.jsx`, `cdash-track.jsx`, `cdash-garage.jsx`, `cdash-rewards.jsx`, `cdash-account.jsx`, `cdash-app.jsx` — **ALL MISSING** (JSX files do not exist in `src/`)
**CSS:** `styles.css`, `dashboard.css`, `cdash.css`
**Existing route:** `/[locale]/(app)/client/home/page.tsx` (basic version)

### CSS-Inferred Sections

Based on `cdash.css` class names, the intended dashboard includes:

| Tab/Section | CSS Classes | Purpose | Backend Status |
|-------------|-------------|---------|----------------|
| **Home / Overview** | `.cd-hero`, `.cd-next` | "Next booking" hero card with detailer mini-card, stats row, CTA buttons | ✅ Appointments + detailer profile exist |
| **Services** | `.cd-svc`, `.cd-svc.on` | Service selection tiles with name, price, meta, popularity badge | ✅ Services catalog exists |
| **Vehicles / Garage** | `.veh-card`, `.veh-img`, `.veh-name`, `.veh-meta`, `.veh-stats` | Vehicle cards with image, name, stats (services, last visit) | ✅ Vehicles CRUD exists |
| **Subscriptions** | `.sub-card`, `.sub-card.active` | Subscription management cards with price + status | ❌ No subscription system |
| **Bookings** | `.ba-grid`, `.ba-photo` | Before/after photo grid | ✅ Photos exist |
| **Track (Live)** | `.track-map`, `.track-pulse`, `.track-pin-home`, `.track-eta-pill` | Live map with detailer location + ETA | ✅ WebSocket endpoint exists |
| **Timeline** | `.tl`, `.tl-row`, `.tl-dot`, `.tl-time` | Appointment status timeline | ✅ FSM statuses exist |
| **Live Status** | `.live-banner`, `.live-pulse` | Active job status banner | ✅ |
| **Rewards** | `.reward-card`, `.reward-tier`, `.reward-pts`, `.reward-progress`, `.reward-bar` | Loyalty points/progress card | ❌ No loyalty system |
| **Addresses** | `.addr-card`, `.addr-ic-wrap` | Saved address cards | ✅ Address endpoints exist |
| **Payment Methods** | `.pay-card`, `.pay-num`, `.pay-meta` | Visual payment card display | ✅ Payment method endpoints exist |
| **Favorite Detailers** | `.fav-card`, `.fav-avi`, `.fav-name`, `.fav-stats` | Saved favorite detailers with stats | ✅ Favorites endpoints exist |
| **Recommendations** | `.rec-card`, `.rec-ic-big` | Service recommendation cards | ❌ No recommendation engine |
| **Day/Time Picker** | `.day-pick`, `.day-btn`, `.slot-pick`, `.slot-btn` | Calendar date + time slot selection | ✅ Availability slots exist |
| **Receipt** | `.rcpt`, `.rcpt-row`, `.rcpt-total` | Job receipt/breakdown | ✅ Payment data exists |
| **In-Progress Banner** | `.ip-banner`, `.ip-banner-h` | Active booking visual indicator | ✅ |
| **Empty State** | `.empty-illus`, `.emoji` | Empty state illustrations | ✅ EmptyState component exists |

### JSX Gap

The customer dashboard is the only page where the JSX component files **were not generated**. The HTML shell references 10 JSX files (`cdash-*.jsx`) that do not exist in `src/`. Only `cdash.css` (614 lines) exists with styling for all the intended components.

**Impact:** Customer dashboard must be built from scratch using `cdash.css` as the style reference. Components identified from CSS patterns:
- DashboardShell (layout)
- DashboardHome (overview + next booking)
- BookingsView (list + detail + timeline)
- TrackView (live map)
- GarageView (vehicle cards)
- RewardsView (loyalty)
- AccountView (profile, addresses, payment methods)

---

## 6. Provider Dashboard

**File:** `raycarwash/project/Provider Dashboard.html`
**JSX sources:** `dash-app.jsx`, `dash-shell.jsx`, `dash-overview.jsx`, `dash-jobs.jsx`, `dash-schedule.jsx`, `dash-services.jsx`, `dash-earnings.jsx`, `dash-reviews.jsx`, `dash-customers.jsx`, `dash-data.jsx`, `dash-icons.jsx`
**CSS:** `dashboard.css`
**Existing route:** `web/portal/(app)/detailer/`
**Backend plan:** `11-provider-dashboard.md`

### Views

| View | Component | Backend Status |
|------|-----------|----------------|
| **Overview** | `dash-overview.jsx` | KPIs (jobs, earnings, rating), quick calendar, recent activity feed | Planning |
| **Jobs** | `dash-jobs.jsx` | Job list with status filter, job detail expand | ✅ Appointments exist |
| **Schedule** | `dash-schedule.jsx` | Calendar + daily breakdown with time slots | Planning |
| **Services** | `dash-services.jsx` | Toggle services on/off, custom pricing | ✅ Provider services exist |
| **Earnings** | `dash-earnings.jsx` | Charts, payout history, cash-out button | Planning |
| **Reviews** | `dash-reviews.jsx` | Review list with response capability | ✅ Reviews exist |
| **Customers** | `dash-customers.jsx` | Client list, booking history, add note | Planning |

---

## 7. Auth Pages

| Page | File | Status |
|------|------|--------|
| Customer Login | `Customer Login.html` | ✅ Auth flow exists |
| Customer Signup | `Customer Signup.html` | ✅ Auth flow exists |
| Provider Login | `Provider Login.html` | ✅ Auth flow exists |
| Provider Signup | `Provider Signup.html` | ✅ Auth flow exists |
| Staff Login | `Staff Login.html` | ✅ Admin auth exists |

---

## 8. Cross-Cutting Observations

### Shared Components Across Pages

| Component | Used In | Status |
|-----------|---------|--------|
| `Navbar` | Landing, Customer, Detailers, Mechanic (4 variations) | Need 4 navbars or 1 configurable |
| `Footer` | Landing, Customer, Detailers, Mechanic, Provider Dashboard | Redesign needed |
| `PhoneMock` / `PhoneFrame` | Landing (Hero), Customer (Hero + BookingJourney), Detailers (Tools) | New component |
| `TweaksPanel` | All pages (design tool, NOT for production) | **Remove in production** |
| `Icons` (via `icons.jsx`) | All pages | Replace with `lucide-react` equivalents |
| FAQ pattern | Landing, Customer, Detailers, Mechanic | Consistent pattern; parametrize |

### CSS Architecture

| File | Used By | Lines |
|------|---------|-------|
| `styles.css` | All pages (shared design system) | 1,115 |
| `customer.css` | Customer Page only | ? |
| `detailers.css` | Detailers Page only | ? |
| `mechanic.css` | Mechanic Page only | ? |
| `dashboard.css` | Provider Dashboard + Customer Dashboard | ? |
| `cdash.css` | Customer Dashboard only | 614 |

The shared `styles.css` contains the design system (CSS variables, typography, buttons, layout) — should be converted to Tailwind v4 config.

### Backend Gaps Summary

| Feature | Pages Affected | Backend Action |
|---------|---------------|----------------|
| Coverage/ZIP check | Landing | New endpoint |
| Reviews aggregate stats | Customer Page | New endpoint |
| Earnings calculator with live data | Detailers Page | New endpoint |
| Waitlist signup | Mechanic Page | New endpoint |
| Subscription/loyalty | Customer Dashboard | New models + endpoints |
| Recommendation engine | Customer Dashboard | Future feature |

### Theme

The design uses a consistent theme:
- **Primary color:** Blue (`#2563eb`) with emerald and orange variants in the `TweaksPanel` (design tool only)
- **Fonts:** Inter (body) + Space Grotesk (headings) + JetBrains Mono (mono) — `cdash.css` references monospace
- **Neutrals:** Zinc palette (ink-50 through ink-900)
- **Radius:** `--radius-sm: 10px`, `--radius-md: 14px`, `--radius-lg: 20px`
- **Shadows:** 3-tier system (sm, md, lg)
- **Dark sections:** `dark-section` with light text on dark backgrounds
