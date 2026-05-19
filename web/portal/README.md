# marketing

Public landing / marketing site for RayCarWash.

- Next.js 16 (App Router) + React 19 + Tailwind 4 + TypeScript
- Bilingual EN/ES via `next-intl`
- Login connected to the existing FastAPI `/auth/login` (admins jump to the admin dashboard; clients land on a welcome screen with app store links)

## Dev

```powershell
cp .env.example .env
npm install
npm run dev
```

Runs on http://localhost:3001 (admin dashboard already uses 3000).

## Env

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | FastAPI backend (defaults to http://localhost:8000) |
| `NEXT_PUBLIC_ADMIN_URL` | Admin dashboard URL — admins redirect here after login |
| `NEXT_PUBLIC_APPSTORE_URL` / `NEXT_PUBLIC_PLAYSTORE_URL` | Mobile app store links |
| `NEXT_PUBLIC_CONTACT_EMAIL` | Contact email shown in footer / contact section |

## Structure

- `app/[locale]/` — localized pages (`/`, `/login`, `/welcome`, `/legal/privacy`, `/legal/terms`)
- `components/` — `Navbar`, `Footer`, `LanguageSwitcher` + `sections/*` (Hero, HowItWorks, Services, ForDetailers, Testimonials, FAQ, ContactCTA)
- `messages/{en,es}.json` — all user-facing copy
- `i18n/` — `routing`, `request`, `navigation` (next-intl wiring)
- `lib/` — `api.ts` (axios + login), `auth.ts` (localStorage tokens, JWT role decode)
- `proxy.ts` — locale negotiation middleware (Next 16 renamed `middleware` → `proxy`)

## Adding a section / copy

1. Add the strings to both `messages/en.json` and `messages/es.json` under a new namespace.
2. Create a new component under `components/sections/` and read with `useTranslations('your-namespace')`.
3. Import and render it inside `app/[locale]/page.tsx`.
