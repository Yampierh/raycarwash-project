# 17 — Waitlist System

> **Status:** Planning
> **Priority:** Medium
> **Dependencies:** `15-marketing-content-cms.md` (admin UI), `16-coverage-zip-service.md` (zip-level waitlist), `infrastructure/email/` (transactional email)
> **Audit findings resolved:** N/A
> **Design source:** `web/portal/components/sections/mechanic/MechanicHero.tsx` + `MechanicCTA.tsx` (mechanic waitlist forms), `Coverage.tsx` (notify-me on unsupported ZIPs)

---

## 1. Objective

A generalized waitlist system that powers:

1. **Mechanic vertical waitlist** (current /mechanic page asks for emails) — current frontend uses `useState` only.
2. **Coverage waitlist** ("notify me when you serve my ZIP") — overlaps with plan 16's `WaitlistedZip`.
3. **Future verticals** (e.g. boat detailing, RV cleaning) — same surface, new source.
4. **Founding-mechanic application** ("Apply as founding mechanic") — captures full application, not just email.

The system stores signups, prevents duplicates, sends confirmation emails, and surfaces an admin queue for ops/marketing to act on.

---

## 2. Hardcoded data on `/mechanic` today

```jsx
// MechanicHero.tsx
const [email, setEmail] = useState("");
const [submitted, setSubmitted] = useState(false);
function submit(e) {
  e.preventDefault();
  if (!email.trim()) return;
  setSubmitted(true);   // ← state only, never persisted
}
```

```jsx
// MechanicCTA.tsx (same pattern, separate form)
```

Both forms vanish into local component state. No server call. No persistence.

---

## 3. Architecture

### 3.1 Waitlist sources (initial set)
| Source slug | Fired by | Captures |
|---|---|---|
| `mechanic_customer` | `/mechanic` hero + bottom CTA | Email + optional ZIP |
| `mechanic_provider` | `/mechanic` "Apply as founding mechanic" CTA | Email + business name + ASE codes + experience years |
| `coverage_zip` | `/` and `/riders` ZIP check on unsupported ZIPs | Email + ZIP |
| `future_vertical_*` | Future pages (e.g. `/boat-detail`) | Email + custom fields |

### 3.2 Model
```
WaitlistEntry
  id (uuid)
  source (string — see table above)
  email (string, lowercase, indexed)
  status (enum: pending | confirmed | invited | converted | unsubscribed)
  utm_source, utm_medium, utm_campaign (capture marketing attribution)
  payload_json (source-specific fields)
  confirmed_at (after email link click)
  invited_at (when admin/system invites them to beta)
  converted_at (when they sign up for the actual service)
  user_id (nullable, set on conversion)
  unsubscribed_at
  ip (audit, retention 30 days)
  user_agent (truncated, audit)
  referrer_url
  created_at
```

Unique constraint: `(source, lower(email))` — one entry per email per source.

### 3.3 Status flow
```
new submission → status="pending" → send confirmation email
                                  ↓ user clicks link
                                  status="confirmed"
                                  ↓ admin batch-invite
                                  status="invited" + send beta access email
                                  ↓ user creates account
                                  status="converted" (linked to user_id)
```

---

## 4. API endpoints

### 4.1 Public
- `POST /api/v1/waitlist`
  ```json
  { "source": "mechanic_customer", "email": "you@example.com", "payload": { "zip": "46802" } }
  ```
  → `200 { ok: true, position?: 347 }` or `409 { ok: false, reason: "already_subscribed" }`.
- `GET /api/v1/waitlist/confirm?token=` — email-link landing → marks `confirmed_at`.
- `POST /api/v1/waitlist/unsubscribe` — by token or email + confirmation step.
- `GET /api/v1/waitlist/position?email=&source=` — show "you're #X in line" (optional, rate-limited).

### 4.2 Admin
- `GET /api/v1/admin/waitlist?source=&status=&cursor=` — paginated list with filters.
- `GET /api/v1/admin/waitlist/summary` — counts per source per status, conversion funnel.
- `POST /api/v1/admin/waitlist/invite` — batch invite (body: `{ entry_ids: [], message? }`) → marks `invited`, sends emails.
- `POST /api/v1/admin/waitlist/export?source=&since=` — CSV export.
- `DELETE /api/v1/admin/waitlist/{id}` — admin hard-delete (GDPR).

---

## 5. Anti-abuse & data hygiene

| Concern | Mitigation |
|---|---|
| Email validation | RFC 5322 + DNS MX check + reject disposable domains (use a maintained blocklist) |
| Spam submissions | Rate limit by IP (5/min) + by email (1/hour for same source) |
| Bot signups | hCaptcha invisible challenge on form; only enforced if rate spikes |
| Fake emails | Require email-link confirmation before counting `confirmed_at` |
| Unsubscribe | One-click unsubscribe link in every email (CAN-SPAM compliance) |
| Audit retention | IP/UA dropped after 30 days; email retained until user requests deletion |
| GDPR / data deletion | Admin DELETE endpoint cascades audit log entries |

---

## 6. Confirmation emails

Templates (managed via plan 15 §6):

### 6.1 `waitlist_confirm_mechanic_customer`
- Subject: "Welcome to the RayCarWash mobile mechanic waitlist"
- Variables: `email`, `confirm_url`, `position`, `expected_launch_text`
- One-tap confirm link → marks `confirmed`.

### 6.2 `waitlist_invite_mechanic_customer`
- Subject: "Your turn — RayCarWash mobile mechanic is live in your area"
- Variables: `email`, `signup_url`, `intro_offer_text`
- Sent in admin-triggered batches.

### 6.3 `waitlist_confirm_coverage`
- Subject: "We'll let you know when we serve {zip}"
- Sets expectation: "We're expanding monthly. Avg wait: 4–8 weeks."

### 6.4 `waitlist_invite_coverage`
- Subject: "{zip} is live — book your first detail"

### 6.5 Common
- `waitlist_unsubscribe_confirm` — confirmation of unsubscription.

---

## 7. Frontend integration

### 7.1 Replace local state with API call

`MechanicHero.tsx`:
```ts
async function submit(e: React.FormEvent) {
  e.preventDefault();
  const res = await fetch("/api/v1/waitlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source: "mechanic_customer", email }),
  });
  if (res.ok) setSubmitted(true);
  else setError(await res.text());
}
```

Same for `MechanicCTA.tsx` and `Coverage.tsx` (notify-me).

### 7.2 Founding-mechanic application
The "Apply as founding mechanic" CTA in `MechanicProviderCTA.tsx` posts to `/waitlist` with `source=mechanic_provider` and a fuller payload:
```json
{
  "email": "...",
  "business_name": "...",
  "ase_codes": ["A4", "A6"],
  "experience_years": 8,
  "city": "Fort Wayne",
  "has_van": true,
  "has_lift": true
}
```

A separate multi-step form page should be built at `/mechanic/apply` for this richer payload.

### 7.3 "Position" display
Optional — show "you're #347 in line" using `GET /waitlist/position`. Cache aggressively; rate-limit to prevent crawlers.

---

## 8. Admin UI

New section in `web/admin/`:
- `/admin/waitlist` — overview cards (one per source) + recent signups + conversion funnel.
- `/admin/waitlist/{source}` — full list, filterable.
- `/admin/waitlist/{source}/invite` — batch invite flow (select entries, customize message, send).
- `/admin/waitlist/exports` — CSV export history.

Each row shows: email, status, days since signup, payload (vehicle, ZIP, etc.), source, last action.

---

## 9. Execution phases

### Phase 1 — Core (Week 1)
- `WaitlistEntry` model + migration.
- `POST /waitlist` + `GET /waitlist/confirm` + `POST /waitlist/unsubscribe` endpoints.
- Email templates (5 above) — `waitlist_confirm_*`, `waitlist_invite_*`, `waitlist_unsubscribe_confirm`.
- Marketing forms (`MechanicHero`, `MechanicCTA`, `Coverage`) wired to API.

### Phase 2 — Admin (Week 2)
- `GET /admin/waitlist*` endpoints.
- Admin UI for list + invite + export.
- Founding-mechanic richer application form at `/mechanic/apply`.

### Phase 3 — Hardening (Week 3)
- Rate limiting + hCaptcha integration.
- Disposable email blocklist.
- Email link confirmation flow polish.
- Conversion tracking (link `user_id` on signup).

### Phase 4 — Analytics (Week 4+)
- Funnel metrics (signups → confirmed → invited → converted).
- Source attribution dashboard.
- Auto-invite rules ("when ZIP is launched, invite all `coverage_zip` entries for that ZIP").

---

## 10. Verification

- [ ] `POST /waitlist` creates an entry and triggers a confirmation email
- [ ] Duplicate submission for same `(source, email)` returns 409
- [ ] Confirmation link marks `confirmed_at` and is single-use
- [ ] Unsubscribe link marks `unsubscribed_at` and prevents future emails
- [ ] Admin batch-invite sends emails and updates statuses atomically (transaction)
- [ ] Conversion attribution: when waitlisted user signs up via their invite link, `converted_at` + `user_id` are set
- [ ] Rate limit blocks 6th submission from same IP in <1 min
- [ ] Disposable email (e.g. `mailinator.com`) is rejected with 422
- [ ] CAN-SPAM compliance: unsubscribe link in every email, physical address in footer
- [ ] CSV export downloads correctly with all PII fields properly encoded
- [ ] Frontend forms (3) show success/error states accurately
- [ ] `GET /waitlist/position` is consistent within a 5-minute window (caching)

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Bot signups inflate apparent demand | hCaptcha + email confirmation gate; only count `confirmed` for metrics |
| Email-confirm flow drops too many users | Make confirmation optional for low-friction signup; track both unconfirmed + confirmed counts |
| Hot ZIP gets hundreds of signups before launch | Admin batch-invite + ramp-up plan (don't invite all at once) |
| Founding-mechanic applications include sensitive PII (SSN for background check) | Don't capture SSN in waitlist; redirect to formal onboarding once approved |
| Multiple waitlists confuse users | Use clear copy per source ("mechanic" vs "coverage"); unify unsubscribe across all sources |
| Email deliverability degrades with rapid growth | Use a transactional email provider (Postmark/SES) with proper SPF/DKIM/DMARC |
| Spam complaint impacts domain reputation | Honor unsubscribe within seconds; never email without explicit confirmation |
| `payload_json` schema drift | JSON schema per source + validation at submit time |

---

## 12. Out of scope

- **Drip campaigns** to waitlist members (separate marketing-automation plan)
- **Referral mechanics** for waitlist positions ("invite 3 friends to skip the line") — could be added later
- **SMS-based waitlist signup** (email-first for V1; SMS confirmation deferred)
- **Public leaderboard / position viewing** beyond the simple "#X in line" display
- **Multi-language waitlist emails** (Phase 1 EN-only; ES added via plan 15 templates)
