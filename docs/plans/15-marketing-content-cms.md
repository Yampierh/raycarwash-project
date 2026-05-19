# 15 — Marketing Content / Admin CMS

> **Status:** Planning
> **Priority:** Medium
> **Dependencies:** existing admin auth, admin dashboard at `web/admin/`, portal at `web/portal/`
> **Audit findings resolved:** N/A
> **Design source:** Audit of `web/portal/messages/{en,es}.json` and current marketing pages — identifies content that's hardcoded today but should be admin-controlled.

---

## 1. Objective

Many of the strings, lists, and stats on the marketing site are **business-controlled content** that should change without a code deploy. This plan introduces a lightweight admin CMS at `web/admin/content/*` that lets non-engineers manage:

1. **Testimonials** (8 on landing + 8 on /riders + 3 on /detailers)
2. **FAQ items** (4 namespaces × 6-8 items each)
3. **Headline stats** (currently softened, but eventually backed by real numbers — admin sets when to expose them)
4. **Coverage areas** (currently hardcoded list; should be a table)
5. **Services catalog presentation** (display order, "Most popular" flag, marketing copy distinct from booking copy)
6. **Add-ons catalog** (same: display order + marketing copy)
7. **Rollout phases on /mechanic** (phase labels + active phase indicator)
8. **Insights/recommendations defaults** (used by Provider Dashboard insight rules until LLM phase)
9. **Loyalty tier perks copy** (admin-tunable per plan 13)
10. **Email/SMS templates** (welcome, booking-confirm, payout-sent, win-back, etc.)

---

## 2. Why an admin CMS instead of i18n-only?

| Concern | i18n alone | i18n + CMS |
|---|---|---|
| Translator edits homepage copy | ✅ pull request | ✅ same |
| Marketing changes 4 testimonials weekly | ❌ requires deploy | ✅ admin click |
| Operations changes "starting from $X" pricing | ❌ requires deploy | ✅ admin click |
| Coverage area expands to a new ZIP | ❌ requires deploy | ✅ admin click |
| A/B test 2 hero variants | ❌ hard | ✅ flag-based |
| Audit who changed what | ❌ git only | ✅ audit log |
| Multi-locale fallback | ✅ next-intl | ✅ same — CMS returns `{en, es}` |

The CMS isn't a replacement for i18n — it's a **runtime store of editable content blocks** that the pages read from. Static labels stay in `messages/{en,es}.json`.

---

## 3. Content audit — what's hardcoded today

| Page | Section | Currently | Should be |
|---|---|---|---|
| Landing | `nav.audienceRiders/Detailers` | i18n | i18n (static) |
| Landing | `hero.h1Client/Detailer` | i18n | i18n (static) |
| Landing | `hero.bulletsClient/Detailer` | i18n | **CMS** (admin reorders/edits) |
| Landing | `coverage.areas[]` (6 entries) | i18n | **CMS** (admin adds/removes) |
| Landing | `services.items[]` (3 entries with prices) | i18n + future API | **API + admin override copy** |
| Landing | `testimonials.items[]` (4 entries) | i18n | **CMS** (admin curates) |
| Landing | `faq.items[]` (8 items) | i18n | **CMS** |
| /riders | `reviewsWall.items[]` (8 entries) | i18n | **CMS** |
| /riders | `compare.services[]` + `rows[]` + `addons[]` | i18n | **API + admin override copy** |
| /riders | `safety.pillars[]` (4 entries) | i18n | **CMS** |
| /riders | `safety.dispute.stats[]` (3 entries) | i18n | **CMS** (numeric placeholders today) |
| /riders | `faq.items[]` (8 items) | i18n | **CMS** |
| /detailers | `tools.items[]` (3 entries) | i18n | **CMS** |
| /detailers | `requirements.items[]` + `steps[]` | i18n | **CMS** |
| /detailers | `testimonials.items[]` (3 entries) | i18n | **CMS** |
| /detailers | `faq.items[]` (7 items) | i18n | **CMS** |
| /detailers | `week` sample schedule (hardcoded in `WeekInLife.tsx`) | TSX | **CMS** (admin edits sample week per locale) |
| /mechanic | `services.items[]` (8 entries) | i18n | **API** (live mechanic services catalog) |
| /mechanic | `how.steps[]` (4 entries) | i18n | **CMS** |
| /mechanic | `providerCta.reqs[]` + `perks[]` | i18n | **CMS** |
| /mechanic | `faq.items[]` (6 items) | i18n | **CMS** |
| /mechanic | `cta.rollout[]` (5 phases) | i18n | **CMS** (admin marks active phase) |
| /mechanic | hero `badge` ("Coming soon · Fort Wayne") | i18n | **CMS** (admin toggles when live) |
| Footer | tagline, `links[]`, `copyright` | i18n + dynamic year | i18n |
| Provider Dashboard | KPI delta thresholds, insight rules | TS constants | **Admin config** |
| Provider Dashboard | Tier names + criteria | TS constants | **Admin config** (plan 11 §5.2) |
| Customer Dashboard | Loyalty tier perks, point earning rates | TS constants | **Admin config** (plan 13 §7) |

---

## 4. CMS architecture

### 4.1 Content model
```
ContentBlock
  id (uuid)
  slug (string, e.g. "testimonial-maria-g", "faq-rider-payment-safety")
  type (enum: testimonial | faq_item | coverage_area | rollout_phase |
              service_card | addon_card | tool_card | safety_pillar |
              dispute_stat | review_wall_item | week_sample_day |
              support_article | rich_text)
  status (draft | published | archived)
  locale (en | es) — block exists per locale
  payload_json (type-specific shape, validated server-side via JSON Schema)
  display_order (integer for collection sorts)
  ab_variant (string, optional — for split-tests)
  page_slug (string — "landing", "riders", "detailers", "mechanic")
  section_slug (string — "testimonials", "faq", "coverage", etc.)
  created_by (user_id)
  updated_by (user_id)
  published_at
  created_at
  updated_at
  deleted_at (soft delete)
```

### 4.2 Collections (logical groupings of blocks)
| Collection | Type | Page · Section |
|---|---|---|
| `landing.testimonials` | testimonial | landing · testimonials |
| `landing.faq` | faq_item | landing · faq |
| `landing.coverage` | coverage_area | landing · coverage |
| `riders.reviews` | review_wall_item | riders · reviewsWall |
| `riders.faq` | faq_item | riders · faq |
| `riders.safety.pillars` | safety_pillar | riders · safety |
| `riders.safety.stats` | dispute_stat | riders · safety.dispute |
| `riders.compare.addons` | addon_card | riders · compare.addons |
| `detailers.tools` | tool_card | detailers · tools |
| `detailers.requirements` | requirement_item | detailers · requirements |
| `detailers.steps` | step_card | detailers · requirements.steps |
| `detailers.testimonials` | testimonial | detailers · testimonials |
| `detailers.faq` | faq_item | detailers · faq |
| `detailers.week` | week_sample_day | detailers · week |
| `mechanic.how` | step_card | mechanic · how |
| `mechanic.requirements` | requirement_item | mechanic · providerCta |
| `mechanic.perks` | perk_row | mechanic · providerCta |
| `mechanic.faq` | faq_item | mechanic · faq |
| `mechanic.rollout` | rollout_phase | mechanic · cta |

### 4.3 Singletons (admin-toggled settings, not collections)
```
ContentSetting
  key (string, unique — e.g. "mechanic.hero.badge", "stats.reviews_count")
  value_json
  description (admin-facing)
  type (text | number | boolean | enum | url)
  page_slug
  locale (nullable — locale-agnostic if null)
  is_public (true = exposed via public API; false = admin-only)
  updated_by
  updated_at
```

Examples:
- `mechanic.hero.badge` = `"Coming soon · Fort Wayne"` (toggle when launched)
- `stats.show_real_numbers` = `false` (when true, expose computed stats; when false, soft phrasing)
- `landing.hero.audience_default` = `"client"` (default audience toggle)
- `coverage.show_zip_check` = `true`
- `mechanic.cta.active_phase` = `"phase_1"` (which rollout phase is current)

---

## 5. API endpoints

### 5.1 Public read endpoints (consumed by marketing site at request time)
- `GET /api/v1/content/collections/{collection_slug}?locale=` — returns published blocks for a collection.
- `GET /api/v1/content/settings?page=&locale=` — returns settings for a page (public ones only).
- `GET /api/v1/content/page/{page_slug}?locale=` — composite: all collections + settings for a page in one call.

These are heavily cached (CDN + Redis, 5-min TTL, ETag-based revalidation). Invalidated by admin publish events.

### 5.2 Admin endpoints (under `/api/v1/admin/content/*`)
- `GET /admin/content/collections/{slug}?locale=&status=` — admin list (incl. drafts).
- `POST /admin/content/blocks`.
- `PATCH /admin/content/blocks/{id}` — partial update.
- `DELETE /admin/content/blocks/{id}` (soft).
- `POST /admin/content/blocks/{id}/publish`.
- `POST /admin/content/blocks/{id}/unpublish`.
- `POST /admin/content/blocks/reorder` — bulk display_order update.
- `GET/PUT /admin/content/settings/{key}` — singleton management.
- `GET /admin/content/blocks/{id}/history` — audit trail.

### 5.3 Validation
Each block `type` has a JSON Schema validator. Examples:
- `testimonial`: `{ quote: string, name: string, city: string, rating: 1..5, avatar_url?: string }`.
- `faq_item`: `{ q: string, a: string, category?: string }`.
- `coverage_area`: `{ name: string, primary: bool, center_lat?: number, center_lng?: number, radius_mi?: number }`.

---

## 6. Email/SMS template management

Separate sub-system but lives in the same CMS spirit.

### 6.1 Model
```
NotificationTemplate
  id, key (e.g. "booking_confirmed", "payout_sent", "winback_offer"),
  channel (email | sms | push),
  locale,
  subject (email only),
  body_template (Handlebars/Liquid),
  preheader (email only),
  variables_json (allowed vars + sample data),
  is_active,
  updated_by, updated_at
```

### 6.2 Admin endpoints
- `GET /admin/notification-templates`.
- `GET/PATCH /admin/notification-templates/{key}?channel=&locale=`.
- `POST /admin/notification-templates/{key}/preview` — render with sample data + send to admin email.
- `POST /admin/notification-templates/{key}/send-test` — send to a target email/phone.

### 6.3 Templates needed (initial set)
- Welcome email (client / detailer)
- Booking confirmed
- Booking reminder (24h, 1h before)
- Detailer en route
- Service complete + review request
- Cancellation refund
- Payout sent
- Promo / win-back
- Tax form ready
- Waitlist confirmation (mechanic)
- Verification status changed
- Password reset
- Account paused / deleted

---

## 7. Admin UI

New section in `web/admin/`:
- `/admin/content` — overview with collection cards + last-updated.
- `/admin/content/collections/{slug}` — list view with drag-handle reorder + inline edit + publish toggle.
- `/admin/content/blocks/{id}` — full editor (form fields per type + rich-text where applicable + locale switcher).
- `/admin/content/settings` — flat list of singletons grouped by page.
- `/admin/content/templates` — email/SMS template editor.

UI patterns:
- Locale switcher (EN | ES) on every page; warn if a block is missing a locale.
- Preview pane that renders the page section with current draft.
- Publish workflow: draft → review → published. Optional schedule-publish.
- Diff view between current published version and draft.

---

## 8. Caching & invalidation

| Layer | TTL | Invalidation |
|---|---|---|
| CDN (Cloudflare/Vercel) | 5 min | On publish, send purge request via API |
| Next.js ISR | 60s revalidate | On publish, trigger on-demand revalidation `/api/revalidate?path=` |
| Redis (admin API cache) | 1 min | On publish, delete by key prefix |
| Browser SWR | session | `Cache-Control: public, s-maxage=300, stale-while-revalidate=60` |

Marketing pages remain **statically generated** with on-demand revalidation. CMS content is fetched at build time and at revalidation triggers — no client-side fetching for SEO-critical content.

---

## 9. Migration plan

### 9.1 From i18n to CMS
1. Build CMS infrastructure (model, endpoints, admin UI) — no consumer changes yet.
2. **Seed CMS from current i18n JSON** via one-time migration script. Each collection's content is copied as published blocks.
3. Refactor each marketing section to read from CMS instead of i18n:
   - Pure layout/labels stay in `useTranslations`
   - List items (testimonials, FAQ, etc.) come from `getContentCollection('landing.testimonials', locale)`
4. Add fallback: if CMS returns empty, fall back to i18n value (during transition).
5. Once stable, remove the duplicated keys from i18n files.

### 9.2 Per-page rollout
- Phase 1: Testimonials (lowest risk, most likely to need frequent edits).
- Phase 2: FAQ items.
- Phase 3: Coverage areas + rollout phases.
- Phase 4: Safety pillars + tool cards + requirements.
- Phase 5: Stats settings (with feature flag for "show real numbers").
- Phase 6: Notification templates.

---

## 10. Verification

- [ ] Admin can create a testimonial, save as draft, preview, publish.
- [ ] Published testimonial appears on marketing landing within 60s (ISR revalidation).
- [ ] EN testimonial appears for EN visitor; ES visitor sees fallback or "Missing translation" admin warning.
- [ ] Reorder drag-handle persists `display_order`.
- [ ] Soft-deleted block is hidden from public API but visible in admin trash.
- [ ] Audit log records every edit with admin user and diff.
- [ ] Schema validation rejects malformed blocks (e.g. testimonial without `quote`).
- [ ] Composite `/content/page/{slug}` returns under 100ms when cached.
- [ ] Cache purge fires on publish and propagates to CDN.
- [ ] Notification template `send-test` delivers a real email/SMS to admin.
- [ ] Marketing site falls back to i18n if CMS endpoint is unreachable (no user-facing breakage).
- [ ] Removing a published block from CMS reverts to i18n fallback or empty state.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Marketing team edits and ships incorrect copy at scale | Required review step before publish; staging preview link |
| CMS becomes single point of failure for marketing pages | Always have i18n fallback bundled in code; CMS is an enrichment layer |
| Schema drift between block type and consumer code | JSON Schema versioned + validated on read; consumer ignores unknown fields |
| Translation parity gaps (block exists in EN, missing ES) | Admin dashboard surfaces parity issues; show warning chip on missing locale |
| Cache invalidation race (visitor sees stale content) | ISR + on-demand revalidation; document expected propagation time (<5 min) |
| Performance regression from per-section CMS fetches | Use composite `/content/page` endpoint; avoid waterfall fetches |
| Admin malicious edit (defacement) | Require 2FA on admin role + audit log + ability to roll back to prior published version |
| Email template variables drift from backend payloads | Backend emits an event registry; template editor validates referenced vars at save time |

---

## 12. Out of scope

- **Full WYSIWYG editor** (use simple form fields + rich-text only on `rich_text` blocks)
- **Marketing automation flows** (drip campaigns, segmentation — separate plan)
- **A/B testing engine** (foundation laid via `ab_variant` field; experiment orchestration deferred)
- **Image/asset CDN** (use existing S3 + Cloudfront)
- **Multi-brand support** (everything assumes single RayCarWash brand)
- **Versioned content publishing** (rollback to prior version is in-scope; full versioning history is deferred)
