# Web & Frontend Issues Analysis

> **Date**: 2026-05-17
> **Scope**: `web/` (Next.js admin), `frontend/` (React Native + Expo), `docs/`, `docker-compose.yml`

---

## 1. Web Admin Dashboard (Next.js 16)

### 1.1 🔴 `web/AGENTS.md` References Non-Existent Docs Directory

**File**: `web/AGENTS.md`

> "Read `node_modules/next/dist/docs/` before writing code there."

**Problem**: The directory `node_modules/next/dist/docs/` does NOT exist. Any agent following these instructions will wait indefinitely or report an error.

**Fix**: Remove or fix the instruction. Next.js 16 does not ship docs in node_modules.

### 1.2 🔴 Web Login Does Not Unwrap Backend Envelope

**File**: `web/lib/api.ts:79`

```typescript
const login = async (email: string, password: string) => {
  const res = await axios.post(BASE_URL + '/auth/login', ...);
  return res.data;  // Raw response, no unwrap()
};
```

If the backend returns envelope-wrapped responses (`{ data: { access_token: ... } }`), the web login would break because it reads `data.access_token` directly. The mobile frontend's `authClient` handles unwrapping via interceptors, but the web uses raw axios.

**Risk**: Backend envelope compliance work would silently break admin login.

### 1.3 🟡 Empty `next.config.ts`

**File**: `web/next.config.ts`

```typescript
const nextConfig: NextConfig = {};
export default nextConfig;
```

No configuration for:
- API proxy rewrites for production builds
- Image optimization (`remotePatterns`)
- Standalone output mode for Docker
- Environment variable validation

### 1.4 🟡 No Server-Side Auth Protection

All dashboard pages use `"use client"`. Auth guard is purely client-side via `useEffect` (file: `web/app/dashboard/layout.tsx`).

**Risk**: A savvy user could bypass by navigating directly to `/dashboard/*` routes and reading static HTML before JS hydration (though API calls would still fail).

### 1.5 🟡 Tokens Stored in localStorage

Web stores JWT in localStorage (keys: `rcw_admin_access`, `rcw_admin_refresh`). This is XSS-vulnerable but standard for SPAs. The mobile frontend correctly uses `expo-secure-store` (encrypted keychain/keystore).

---

## 2. Frontend Mobile (React Native + Expo)

### 2.1 🔴 Button Variant Mismatch — Docs vs Code

| Source | Variants |
|--------|----------|
| `docs/frontend.md` | primary, secondary, ghost, danger, outline |
| `components/Button.tsx` | primary, secondary, ghost, danger, cta |

**Problem**: `outline` variant documented but doesn't exist. `cta` (call-to-action gradient) exists but isn't documented. This causes confusion for developers.

### 2.2 🟡 Hardcoded IP Addresses in Config

**File**: `frontend/src/config/app.config.ts`, `.env.local`, `.env.example`

| File | Value |
|------|-------|
| `app.config.ts` fallback | `http://192.168.0.10:8000` |
| `.env.local` | `http://192.168.0.10:8000` |
| `.env.example` | `http://192.168.0.1:8000` |

Hardcoded IPs won't work for all dev environments and are easily forgotten during deployment. Should use `localhost` or environment detection.

### 2.3 🟢 Two Axios Clients — Correctly Implemented

**Verified**: `authClient` (base `/auth`) and `apiClient` (base `/api/v1`) are correctly separated per AGENTS.md.

### 2.4 🟢 SecureStore Keys — Correctly Implemented

| Key | Exists? |
|-----|---------|
| `raycarwash_jwt_token` | ✅ |
| `raycarwash_refresh_token` | ✅ |
| `raycarwash_onboarding_token` | ✅ |
| `raycarwash_push_token` | ✅ |
| `raycarwash_biometric_enabled` | ✅ |
| `raycarwash_last_email` | ✅ |
| `raycarwash_passkey_enabled` | ✅ |

### 2.5 🟢 WebSocket Hook — Correctly Implemented

**File**: `hooks/useAppointmentSocket.ts`

Validates: auto-connect, exponential backoff (1s → 30s max), 30s heartbeat, close code handling (4001/4003/4004 no reconnect), Kalman filter for GPS.

---

## 3. Documentation Issues

### 3.1 🟡 Stale Documentation

| Doc | States | Actual | Delta |
|-----|--------|--------|-------|
| `docs/frontend.md` | 21 screens | 24 screens | +3 (Phase 3 screens) |
| `docs/frontend.md` | 13 API service files | 22 service files | +9 |

### 3.2 🟡 Integration Plans Stuck on "Planning"

All 6 integration plan files in `docs/integration_plans/` (00-user through 04-vehicles + README) show **"Planning"** status, but the codebase is well past implementation. These are legacy/stale.

### 3.3 🟢 API Docs Well-Maintained

`docs/api.md` (619 lines) covers auth, vehicles, services, detailers, matching, appointments, payments, fares, reviews, notifications, admin, WebSocket, error formats, rate limits. Appears up-to-date.

---

## 4. DevOps / Configuration

### 4.1 🟡 Root `package.json` — Windows Path in `install-deps`

**File**: `package.json`

```json
"install-deps": "python -m venv backend/venv && ./backend/venv/Scripts/pip install ..."
```

Uses POSIX path syntax. On Windows (win32), this may fail depending on shell. `cross-env` is used for `ENV_FILE` but not for the venv path.

### 4.2 🟡 `npm run dev` Omits Web Dashboard

The `dev` script only starts backend + frontend. Developers must discover `npm run dev:web` separately. There IS a `dev:all` script but no mention in AGENTS.md.

### 4.3 🟡 No Postinstall Hook

No `postinstall` script to auto-copy `.env.example` → `.env.local` for frontend. The frontend has a `setup` script but it's not run automatically.

### 4.4 🟡 Docker Compose — No Backend Service

**File**: `docker-compose.yml`

The FastAPI backend is NOT defined as a service. Only Redis, PostgreSQL, MailHog, and RQ workers are in compose. Full-stack Docker development is not possible.

### 4.5 🟡 Redis Without Persistence

```yaml
command: redis-server --save "" --appendonly no
```

All Redis data (rate limiter state, WebSocket rooms, cached data) lost on container restart. Dev-only.

---

## 5. Security Notes

| Aspect | Web | Mobile |
|--------|-----|--------|
| Token storage | localStorage (XSS-vulnerable) | expo-secure-store (encrypted) |
| Auth guard | Client-side `useEffect` | Zustand store + API interceptors |
| CSRF protection | None (Bearer token standard) | None (Bearer token standard) |
| Rate limiting | Backend-only (slowapi) | Backend-only (slowapi) |

---

## Summary — Priority Matrix

| Priority | Action | Location |
|----------|--------|----------|
| P0 | Fix `web/AGENTS.md` docs reference | `web/AGENTS.md` |
| P0 | Add envelope unwrapping to web login | `web/lib/api.ts:79` |
| P1 | Fix Button variant docs vs code | `docs/frontend.md` + `Button.tsx` |
| P1 | Replace hardcoded IPs in frontend config | `frontend/src/config/app.config.ts` |
| P1 | Add `next.config.ts` production config | `web/next.config.ts` |
| P2 | Update stale documentation | `docs/frontend.md` |
| P2 | Remove or update integration plans | `docs/integration_plans/` |
| P2 | Add server-side auth to web admin | `web/app/dashboard/layout.tsx` |
| P3 | Fix `install-deps` Windows path | `package.json` |
| P3 | Add postinstall hook | `package.json` |
| P3 | Add backend service to docker-compose | `docker-compose.yml` |
