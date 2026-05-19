# 12 — Marketing Website Redesign

> **Status:** Phases 1–4 frontend complete · Backend endpoints pending
> **Priority:** High
> **Dependencies:** `11-provider-dashboard.md` (provider dashboard), existing marketing site structure
> **Audit findings resolved:** N/A
> **Design source:** `raycarwash/project/` — Landing Page.html, Customer Page.html, Detailers Page.html, Mechanic Page.html, Customer Dashboard (cdash.css only)

---

## 0. Implementation Status (2026-05-19)

The frontend portion of Phases 1–4 has been implemented. Below is what shipped and what remains.

### What shipped

**Foundations:**
- Design tokens in [marketing/app/globals.css](../../web/portal/app/globals.css): `--brand`, `--brand-soft`, `--brand-softer`, `--brand-ink`, `--sec-pad`, plus full `ink-*` and `brand-*` Tailwind 4 theme tokens.
- Space Grotesk added as `--font-display` in [marketing/app/[locale]/layout.tsx](../../web/portal/app/[locale]/layout.tsx).
- Audience persistence store at [marketing/lib/store/audience.ts](../../web/portal/lib/store/audience.ts) (zustand + localStorage). Controls `client | detailer` audience for the landing page.
- i18n: ~210 new keys added to both [en.json](../../web/portal/messages/en.json) and [es.json](../../web/portal/messages/es.json) under new namespaces `trust`, `coverage`, `ridersPage`, `detailersPage`, `mechanicPage`. Existing `hero`, `how`, `contact` namespaces now have audience-aware variants (`*Client` / `*Detailer`).

**Navigation:**
- [components/Navbar.tsx](../../web/portal/components/Navbar.tsx) auto-detects page variant from pathname (`landing | riders | detailers | mechanic`), exposes audience toggle on landing, page-tab navigation on every other variant, and a variant-aware right CTA.
- [components/Footer.tsx](../../web/portal/components/Footer.tsx) redesigned with 4-column layout, app store buttons, locale strip.

**Landing page sections (all redesigned, audience-aware where applicable):**
| Section | File |
|---|---|
| Hero with rotating phone mock + audience-aware copy/CTAs | [components/sections/Hero.tsx](../../web/portal/components/sections/Hero.tsx) |
| Shared PhoneMock (client + detailer variants, 4 steps each) | [components/sections/PhoneMock.tsx](../../web/portal/components/sections/PhoneMock.tsx) |
| TrustBadges (3 trust strip cards) | [components/sections/TrustBadges.tsx](../../web/portal/components/sections/TrustBadges.tsx) |
| HowItWorks (4-card grid, audience-aware) | [components/sections/HowItWorks.tsx](../../web/portal/components/sections/HowItWorks.tsx) |
| Services (3-tier pricing with featured) | [components/sections/Services.tsx](../../web/portal/components/sections/Services.tsx) |
| Coverage (Fort Wayne map SVG + ZIP check form) | [components/sections/Coverage.tsx](../../web/portal/components/sections/Coverage.tsx) — new |
| ForDetailers (split layout, dark, earnings card) | [components/sections/ForDetailers.tsx](../../web/portal/components/sections/ForDetailers.tsx) |
| Testimonials (4 cards + rating summary) | [components/sections/Testimonials.tsx](../../web/portal/components/sections/Testimonials.tsx) |
| FAQ (accordion, namespace-configurable so /riders & /detailers & /mechanic can reuse) | [components/sections/FAQ.tsx](../../web/portal/components/sections/FAQ.tsx) |
| ContactCTA (audience-aware) | [components/sections/ContactCTA.tsx](../../web/portal/components/sections/ContactCTA.tsx) |

**/riders route** — at [app/[locale]/(marketing)/riders/page.tsx](../../web/portal/app/[locale]/(marketing)/riders/page.tsx):
- RidersHero (with calendar phone mock + main phone)
- BookingJourney (4-tab phone walkthrough)
- ServicesCompare (3-service comparison table + 6 add-ons)
- TrustSafety (4-pillar safety section + dispute card)
- ReviewsWall (8 reviews, varied tile sizes)
- FAQ (reuses base FAQ with `ridersPage.faq` namespace)
- RidersCTA (dark hero + QR code + footnotes)

**/detailers route** — at [app/[locale]/(marketing)/detailers/page.tsx](../../web/portal/app/[locale]/(marketing)/detailers/page.tsx):
- DetailersHero (with earnings preview card)
- EarningsCalc (interactive sliders for jobs/avg/days, computes net after 15% fee)
- WeekInLife (sample 7-day schedule grid)
- Tools (3 phone mocks: dispatcher, route planner, photo capture)
- Requirements (6 reqs list + 4-step start guide)
- DetailersTestimonials (3 detailer quotes)
- FAQ (reuses base FAQ with `detailersPage.faq` namespace)
- DetailersCTA (apply CTA with progress preview)

**/mechanic route (NEW)** — at [app/[locale]/(marketing)/mechanic/page.tsx](../../web/portal/app/[locale]/(marketing)/mechanic/page.tsx):
- MechanicHero (waitlist email signup + toolbox SVG art) — "coming soon" framing
- MechanicServices (8 service cards with prices)
- MechanicHow (4-step preview)
- MechanicProviderCTA (recruit founding mechanics — softened, no $1,200/wk guarantee)
- FAQ (reuses base FAQ with `mechanicPage.faq` namespace)
- MechanicCTA (waitlist signup + rollout phases)

### Business-sensitive content adjustments (per user direction 2026-05-19)

Per user direction, the following softening was applied across all pages:
- **Stats**: Specific numbers ("2,400+ details", "1,240+ reviews", "22 min ETA", "94% disputes resolved") replaced with soft phrasing ("Highly rated", "Fast response", "Trusted by riders").
- **Pricing**: Kept as "starting from $X" — service-level prices and add-on pricing preserved for the public marketing site.
- **Partner names**: References to "Stripe Identity" and "Checkr" generalized to "identity verification" and "background check."
- **SLA commitments**: "$1M per occurrence", "12-mo warranty", "Same-day payouts", "48-hour dispute window" softened to capability claims ("Insured service", "Quick payouts", "Open a dispute and our team reviews promptly").
- **Detailer earnings benchmarks**: Removed specific median/top-quartile dollar figures ($1,840, $2,720, $3,400). Earnings calculator still interactive but presents results as personal projections.
- **Mechanic vertical**: Built as "coming soon" with waitlist signup but no specific dates (Q4 2026, etc.), no "$1,200/wk guaranteed minimum", no "12/20 spots remaining" counters.

### Verification

- ✅ `npx tsc --noEmit` passes with 0 errors (939 files checked).
- ⏳ Visual QA pending — pages have not been started in dev server during this implementation pass.
- ⏳ ES translation parity verified for all new namespaces — keys mirror EN exactly.

### Backend gaps surfaced by this redesign

The frontend uses **fake/local state** for these features because no backend endpoint exists yet. Each needs a backend implementation plan to ship for real.

| Frontend feature | Current state | Backend gap |
|---|---|---|
| **Coverage ZIP check** (landing) | Hardcoded list of 5 ZIPs in [Coverage.tsx](../../web/portal/components/sections/Coverage.tsx) | `GET /api/v1/coverage/zip/{zip}` → returns `{ covered: boolean, eta_at_launch?: string }`. Authoritative source: a `service_zip_codes` table or H3-based geofencing in `infrastructure/h3/`. |
| **Mechanic waitlist signup** (hero + footer CTA on /mechanic) | `useState`, no submission | `POST /api/v1/waitlist` body `{ email, source: "mechanic" }` → returns position. New domain `domains/waitlist/`. Should send a confirmation email via `infrastructure/email/`. |
| **Detailer earnings calculator** (/detailers) | Pure client-side math (`jobs * avg * (1 - 0.15)`) | No backend needed for the calculator itself, but the `0.15` platform fee should come from a config endpoint `GET /api/v1/platform/fee-schedule` so finance can tune it without a frontend deploy. |
| **Booking journey demo** (/riders) | Static walkthrough | No backend needed (this is illustrative of the mobile-app flow). |
| **Service compare table** (/riders) | Hardcoded 8 features × 3 services | Could be wired to `GET /api/v1/services?category=detailing&format=marketing` once a services-catalog endpoint exposes feature flags. Low priority — content is stable. |
| **Mechanic services** (/mechanic) | Hardcoded 8 services | When the mechanic vertical launches, hydrate from `GET /api/v1/services?category=mechanic`. Out of scope until mechanic backend exists. |
| **Reviews wall** (/riders) | 8 hardcoded testimonials | Could pull from `GET /api/v1/reviews?published=true&min_rating=5&limit=8` when the review system is ready. Currently a copy-controlled marketing surface. |

### What's deferred

- **Provider Dashboard** ([raycarwash/project/Provider Dashboard.html](../../raycarwash/project/Provider%20Dashboard.html)) — see [11-provider-dashboard.md](./11-provider-dashboard.md). Has its own dedicated plan with 7 routes under `(app)/detailer/dashboard/*`. Not built in this pass.
- **Customer Dashboard** ([raycarwash/project/Customer Dashboard.html](../../raycarwash/project/Customer%20Dashboard.html)) — has full HTML/JSX in the design bundle (not just CSS as previously documented). Target route is `(app)/client/dashboard/*`. **Recommend a dedicated plan `13-customer-dashboard.md`** before implementation.
- **Marketing visual QA** — `next dev` has not been run during this implementation pass. Pages should be reviewed in a browser before merging.

---

## 1. Objective

Redesign the marketing website (`marketing/app/[locale]/(marketing)/`) to match the visual prototypes in `raycarwash/project/`, including:

1. **Landing Page** — full hero + features + pricing + CTA redesign
2. **Customer (Riders) Page** — redesigned `/riders` page
3. **Detailers Page** — redesigned provider recruitment page
4. **Mechanic Page** — **new** `/mechanic` route
5. **Customer Dashboard** — `cdash.css` provides styling reference; JSX files not generated

---

## 2. Design Feature Map

### 2.1 Landing Page

**Source**: `raycarwash/project/Landing Page.html` + JSX components

| Section | Design Features | Existing (`components/sections/`) | Gap |
|---------|----------------|-----------------------------------|-----|
| **Hero** | Full-viewport hero with gradient background, headline, subtitle, CTA buttons (Get Started + Learn More), phone mockup, stats bar (5K+ washes, 50+ detailers, 4.9 rating) | `Hero.tsx` — basic hero, no stats bar, no phone mockup | ⚠️ Partial — needs full redesign |
| **How It Works** | 4 steps with icons and descriptions in a grid | `HowItWorks.tsx` — 4 steps already | ✅ Exists, may need styling refresh |
| **Services/Pricing** | 3-tier pricing cards (Basic, Premium, Ultimate) with features list and CTA | `Services.tsx` — 3 packages | ⚠️ Needs redesign to match prototype |
| **Why Choose Us** | Trust features grid (Certified Detailers, Eco-Friendly, etc.) | Not in existing marketing site | ❌ New section |
| **Testimonials** | Carousel-style testimonials with ratings | `Testimonials.tsx` | ⚠️ Needs carousel redesign |
| **Download App** | CTA section with app store badges | `ContactCTA.tsx` | ✅ Similar concept |
| **FAQ** | Accordion-style FAQ | `FAQ.tsx` | ✅ Already exists |
| **Footer** | Full footer with links, social, contact | `Footer.tsx` | ⚠️ May need refresh |

### 2.2 Customer (Riders) Page

**Source**: `raycarwash/project/Customer Page.html`

| Section | Purpose | Backend | Status |
|---------|---------|---------|--------|
| **Hero** | "Wash on Your Terms" with booking CTA | N/A (marketing) | ❌ New page |
| **Features Grid** | Mobile booking, real-time tracking, multiple services | N/A | ❌ New |
| **Pricing** | Service pricing comparison | Services catalog | ✅ Can use live data |
| **Coverage Map** | Fort Wayne service area | Provider locations | ⚠️ Needs map integration |
| **CTA** | "Get Started" → signup | Auth | ✅ |

Currently `/riders` page exists but is a basic layout. Needs full redesign.

### 2.3 Detailers Page

**Source**: `raycarwash/project/Detailers Page.html`

| Section | Purpose | Backend | Status |
|---------|---------|---------|--------|
| **Hero** | "Earn on Your Schedule" with stats | N/A | ❌ New |
| **Benefits** | Income potential, flexible schedule, tools | N/A | ❌ New |
| **How It Works** | Signup → Get Approved → Accept Jobs → Get Paid | Registration flow | ⚠️ Needs live steps |
| **Requirements** | Vehicle, equipment, insurance check | Verification flow | ❌ Can reference |
| **Testimonials** | Detailer success stories | Reviews | ✅ |
| **CTA** | "Apply Now" → signup as detailer | Auth | ✅ |

Currently `/detailers` page exists with basic layout. Needs full redesign to match the high-fidelity prototype.

### 2.4 Mechanic Page (NEW)

**Source**: `raycarwash/project/Mechanic Page.html`

| Section | Purpose | Backend | Status |
|---------|---------|---------|--------|
| **Hero** | "Mobile Mechanic Service" with CTA | N/A | ❌ New route + page |
| **Services** | Oil change, brake service, diagnostics, etc. | Mechanic models exist in backend | ⚠️ Services catalog for mechanic vertical |
| **How It Works** | Similar to detailers | N/A | ❌ New |
| **Pricing** | Service pricing | Mechanic pricing | ⚠️ Needs live pricing |
| **CTA** | "Book a Mechanic" | Auth + booking | ⚠️ Booking flow exists but for detailing only |

This is an entirely new route: `/[locale]/mechanic`.

### 2.5 Customer Dashboard

**Source**: `raycarwash/project/cdash.css` (styling only, no JSX components generated)

The CSS references classes for:
- Dashboard layout (sidebar, header, main content area)
- Vehicle cards (`.vehicle-card`, `.vehicle-image`, `.vehicle-info`)
- Appointment timeline (`.timeline`, `.timeline-item`)
- Status badges (`.status-badge`, `.status-scheduled`, `.status-completed`)
- Stats grid (`.stats-grid`, `.stat-card`)
- Service history list (`.history-list`, `.history-item`)

**No JSX components were generated** for the customer dashboard. This means the components need to be designed from scratch, using the CSS as a style reference.

---

## 3. Route Changes

| Route | Action | Design Source |
|-------|--------|---------------|
| `/[locale]/(marketing)/page.tsx` | **Redesign** | `Landing Page.html` |
| `/[locale]/(marketing)/riders/page.tsx` | **Redesign** | `Customer Page.html` |
| `/[locale]/(marketing)/detailers/page.tsx` | **Redesign** | `Detailers Page.html` |
| `/[locale]/(marketing)/mechanic/page.tsx` | **NEW** | `Mechanic Page.html` |
| `/[locale]/(app)/client/dashboard/page.tsx` | **Redesign or NEW** | `cdash.css` (styling ref only) |
| `/[locale]/(app)/client/dashboard/overview/page.tsx` | **NEW** | cdash.css |
| `/[locale]/(app)/client/dashboard/vehicles/page.tsx` | **NEW** | cdash.css |
| `/[locale]/(app)/client/dashboard/history/page.tsx` | **NEW** | cdash.css |

---

## 4. i18n Impact

New messages needed across all namespaces. Estimated ~200 new keys.

| Page | Namespace | Estimated Keys |
|------|-----------|---------------|
| Landing Redesign | `hero`, `features`, `pricing` | ~60 |
| Riders Redesign | `riders` | ~40 |
| Detailers Redesign | `detailers` | ~40 |
| Mechanic (new) | `mechanic` | ~50 |
| Client Dashboard | `clientDashboard` | ~60 |

---

## 5. Component Inventory (from raycarwash/project/)

The design bundle includes JSX components that serve as reference prototypes:

| Page | Components | JSX Files |
|------|-----------|-----------|
| Landing | Hero, FeaturesGrid, PricingCards, StatsBar, TestimonialCarousel, DownloadCTA | `lp-*.jsx` |
| Riders | RidersHero, RiderFeatures, RiderPricing, CoverageMap, RiderCTA | `rp-*.jsx` |
| Detailers | DetailerHero, BenefitsList, StepGuide, Requirements, DetailerTestimonials, ApplyCTA | `dp-*.jsx` |
| Mechanic | MechanicHero, MechanicServices, MechanicHowItWorks, MechanicPricing, MechanicCTA | `mp-*.jsx` |
| Customer Dashboard | (no JSX generated — only `cdash.css`) | N/A |

---

## 6. Execution Phases

### Phase 1 — Landing Page Redesign
- Redesign `Hero.tsx` with gradient background, phone mockup, stats bar
- Redesign `Services.tsx` to match 3-tier pricing cards
- Create new `WhyChooseUs.tsx` section
- Redesign `Testimonials.tsx` with carousel
- Redesign `Footer.tsx` if needed
- Update landing page layout to compose new sections
- Update i18n keys

### Phase 2 — Detailers Page Redesign
- Full redesign of `/[locale]/detailers/page.tsx`
- Create new section components: Hero, Benefits, StepGuide, Requirements
- Integrate with existing `ForDetailers` section patterns
- Update i18n keys

### Phase 3 — Riders Page Redesign
- Full redesign of `/[locale]/riders/page.tsx`
- Create new section components: Hero, Features Grid, Pricing, Coverage Map
- Update i18n keys

### Phase 4 — Mechanic Page (NEW)
- Create new route `/[locale]/mechanic/page.tsx`
- Create mechanic-specific section components: Hero, Services, HowItWorks, Pricing, CTA
- Update i18n keys with new `mechanic` namespace
- Note: mechanic booking flow is out of scope for this phase (marketing only)

### Phase 5 — Customer Dashboard (Client Dashboard)
- Design customer dashboard components from scratch using `cdash.css` as style reference
- Dashboard overview: stats grid (upcoming appointments, vehicles, total spent)
- Vehicles tab: vehicle cards with photo, make/model, last service
- Appointment history tab: filterable/sortable list with timeline view
- Profile/settings tab
- Note: requires user input on whether to create full JSX from scratch

---

## 7. Design-to-Code Migration Notes

| Aspect | Prototype (raycarwash) | Production (marketing/) |
|--------|----------------------|------------------------|
| **Styling** | Raw CSS in `<style>` tags or CSS files | Tailwind v4 utility classes |
| **Data** | Hardcoded mock data | SWR hooks to backend API |
| **Icons** | Various (Font Awesome, Material) | `lucide-react` only |
| **Images** | Local placeholder images | `next/image` optimized |
| **i18n** | English-only hardcoded text | `next-intl` with `useTranslations()` |
| **Responsive** | Desktop-only layout | Mobile-first, responsive |
| **State** | Local React state | Zustand + SWR |
| **Animations** | CSS transitions | Tailwind + Framer Motion (optional) |

---

## 8. Verification

- [ ] Landing page matches prototype design across breakpoints
- [ ] Stats bar shows real platform data (or mock for marketing)
- [ ] Pricing cards use real service catalog data where possible
- [ ] Testimonials carousel works on mobile touch
- [ ] Detailers page matches prototype with all sections
- [ ] Riders page matches prototype with coverage info
- [ ] Mechanic page renders at `/mechanic` route
- [ ] All pages have `<meta>` tags for SEO
- [ ] All text is i18n-ized (no hardcoded English)
- [ ] No regressions on existing pages (about, contact, legal, trust)
- [ ] Lighthouse performance > 85 on desktop
- [ ] Responsive layout works on mobile (320px+)
- [ ] Navigation menus updated with new routes

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Mechanic page references mechanic services that don't exist in live catalog | Use service categories to filter; show placeholder if none configured |
| Customer Dashboard has no JSX components to reference | Design from scratch using `cdash.css` as style guide; present wireframes to user for approval |
| Coverage map requires Google Maps API key | Use static map image with fallback; defer interactive map to future phase |
| Prototype uses raw CSS — full visual match is not guaranteed | Get sign-off per component; iterate if needed |
| No test file exists for the new components | Follow existing test patterns; manual QA for visual fidelity |
