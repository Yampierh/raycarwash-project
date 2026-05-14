# Frontend — Architecture & Developer Guide

Stack: **React Native · Expo 54 · TypeScript strict · React Navigation v7**

---

## Structure

```
frontend/src/
├── config/
│   ├── app.config.ts       # API base URL, support email, app store links, fallback coords (Fort Wayne)
│   └── oauth.ts            # Google/Apple client ID placeholders
│
├── navigation/
│   ├── AppNavigator.tsx    # Root navigator — stack + tabs
│   ├── types.ts            # RootStackParamList, UserRole enum, UserProfile interface
│   └── navigationRef.ts    # Imperative navigation ref (use outside components)
│
├── screens/                # 21 screens total
│   ├── Boot / Auth
│   │   ├── LoadingScreen.tsx           # Splash + token rehydrate, biometric / passkey quick-unlock
│   │   ├── LoginScreen.tsx
│   │   ├── RegisterScreen.tsx
│   │   ├── ForgotPasswordScreen.tsx
│   │   ├── CompleteProfileScreen.tsx   # Bearer onboarding_token
│   │   └── ProviderTypeScreen.tsx      # Service-type fork (Detailer | Continue as Client)
│   ├── Client
│   │   ├── HomeScreen.tsx              # Real-time WS: status banner + detailer location
│   │   ├── ProfileScreen.tsx
│   │   └── EditProfileScreen.tsx
│   ├── Vehicles
│   │   ├── VehiclesScreen.tsx
│   │   ├── AddVehicleScreen.tsx        # VIN lookup → pre-fill form
│   │   ├── VehicleDetailScreen.tsx
│   │   └── SelectVehiclesScreen.tsx    # Multi-vehicle selection for booking
│   ├── Booking
│   │   ├── BookingScreen.tsx           # Step 1: service + addons per vehicle
│   │   ├── ScheduleScreen.tsx          # Step 2: date/time or ASAP
│   │   ├── DetailerSelectionScreen.tsx # Step 3: smart matching results
│   │   └── BookingSummaryScreen.tsx    # Step 4: confirm + payment
│   └── Detailer
│       ├── DetailerOnboardingScreen.tsx
│       ├── DetailerProfileScreen.tsx
│       ├── DetailerServicesScreen.tsx  # Toggle services on/off + custom price
│       └── DetailerHomeScreen.tsx      # WS + GPS push, job timer, status buttons
│
├── components/             # Sprint 9 shared design system — never duplicate inline
│   ├── Button.tsx          # 5 variants (primary/secondary/ghost/danger/outline)
│   ├── Card.tsx
│   ├── StatusBadge.tsx     # Uses Colors.status tokens — pass `status` prop
│   ├── EmptyState.tsx
│   ├── SectionHeader.tsx
│   ├── Typography.tsx      # Wraps TypographyScale (h1, h2, h3, h4, body, label, caption)
│   └── AnimatedInput.tsx   # Focus-animated text input with floating label
│
├── services/               # 13 API service files
│   ├── api.ts              # Axios instances + JWT interceptors + WS_BASE_URL
│   ├── auth.service.ts
│   ├── user.service.ts
│   ├── vehicle.service.ts
│   ├── service.service.ts
│   ├── addon.service.ts
│   ├── appointment.service.ts
│   ├── detailer.service.ts
│   ├── detailer-private.service.ts
│   ├── payment.service.ts
│   ├── review.service.ts
│   ├── notification.service.ts # Expo Push token register / unregister
│   └── rides.service.ts        # /api/v1/rides/* (v2 fare flow)
│
├── hooks/
│   ├── useAppointmentSocket.ts  # WS: auto-connect, backoff, heartbeat, callbacks
│   ├── useLocation.ts           # expo-location GPS hook
│   ├── useDeadReckoning.ts      # Smooths sparse GPS updates with Kalman filter
│   ├── useWeather.ts            # Current weather lookup (used on Home for ASAP warnings)
│   ├── usePushNotifications.ts  # Permission + Expo token register/unregister
│   └── useAppNavigation.ts      # Typed wrapper around useNavigation()
│
├── store/
│   └── authStore.ts        # Zustand: synchronous JWT + roles for WS auth
│
├── utils/
│   ├── storage.ts          # SecureStore wrappers: token, refresh, onboarding, push, biometric/passkey flags, registration-path
│   ├── auth-redirect.ts    # navigateAfterAuth() — routes by role + onboarding state
│   ├── formatters.ts       # Date / money formatters
│   ├── pricing.ts          # Client-side mirror of pricing formula
│   └── kalman.ts           # Kalman filter for GPS smoothing
│
└── theme/colors.ts         # Colors (legacy + semantic tokens) + Spacing + Radius + TypographyScale
```

---

## Navigation structure

```
RootStack
├── Login / Register                    (unauthenticated)
│
├── Main (client bottom tabs)
│   ├── Tab: Home                       → HomeScreen
│   ├── Tab: Vehicles                   → VehiclesScreen
│   └── Tab: Profile                    → ProfileScreen
│
├── DetailerMain (detailer bottom tabs)
│   ├── Tab: Operations                 → DetailerHomeScreen
│   └── Tab: Profile                    → DetailerProfileScreen
│
└── Shared stack / modals
    ├── AddVehicle
    ├── VehicleDetail
    ├── SelectVehicles
    ├── Booking                         (service + addons step)
    ├── Schedule                        (date / ASAP step)
    ├── DetailerSelection               (matching results)
    ├── BookingSummary                  (confirm + pay)
    ├── EditProfile
    ├── DetailerOnboarding
    └── DetailerServices
```

---

## Two Axios clients

**Critical** — never mix them:

```ts
// api.ts
export const authClient = axios.create({ baseURL: `${API_BASE_URL}/auth` });
export const apiClient  = axios.create({ baseURL: `${API_BASE_URL}/api/v1` });
```

| Client | Base | Use for |
|---|---|---|
| `authClient` | `/auth` | identify, verify, complete-profile, social, refresh, sessions, passkeys |
| `apiClient` | `/api/v1` | vehicles, appointments, detailers, services, matching, payments, reviews |

`apiClient` has a 401 interceptor that automatically calls `POST /auth/refresh` and retries the original request.

---

## Auth store (Zustand)

```ts
// store/authStore.ts
interface AuthState {
  token: string | null;
  roles: string[];
  saveToken: (token: string, roles: string[]) => void;
  clearAuthTokens: () => void;
}
```

- Synchronous access — used by WS hook to get token without `await`
- `app.tsx` hydrates from `expo-secure-store` at boot
- `saveToken` and `clearAuthTokens` are called after login/logout

---

## WebSocket hook

```ts
const { sendLocationUpdate } = useAppointmentSocket({
  appointmentId: appt.id,
  onStatusChange: (status) => setStatus(status),
  onLocationUpdate: ({ lat, lng }) => setMarker({ lat, lng }),
});
```

**Behavior:**

- Auto-connects using token from `authStore` (synchronous, no await)
- Exponential backoff: 1s → 2s → 4s → … → 30s max
- Heartbeat ping every 30s to keep connection alive
- `WS_BASE_URL` in `api.ts` replaces `http(s)://` with `ws(s)://` automatically
- Cleans up on unmount

**GPS push (detailer side):**

```ts
// DetailerHomeScreen — while job is IN_PROGRESS
const intervalId = setInterval(async () => {
  const loc = await Location.getCurrentPositionAsync({});
  sendLocationUpdate(loc.coords.latitude, loc.coords.longitude);
}, 5000);
```

---

## Booking flow (4 steps)

| Step | Screen | API |
|---|---|---|
| 1 | SelectVehicles | Local state |
| 2 | Booking | `GET /api/v1/services`, `GET /api/v1/addons` |
| 3 | Schedule | `GET /api/v1/detailers/{id}/availability` or ASAP mode |
| 4 | DetailerSelection | `GET /api/v1/matching` |
| Confirm | BookingSummary | `POST /api/v1/appointments`, `POST /api/v1/payments/create-intent` |

---

## Client onboarding (8 steps)

| Step | Screen | Blocking | API |
|---|---|---|---|
| 1 | Splash — choose role | — | — |
| 2 | Identify (email/phone) | — | `POST /auth/identify` |
| 3 | Verify (password or social) | — | `POST /auth/verify` |
| 4 | Complete profile | — | `PUT /auth/complete-profile` |
| 5 | Contact details (fill gap) | — | `PUT /auth/update` |
| 6 | Add vehicle | **Yes** — no vehicle = no booking | `POST /api/v1/vehicles` |
| 7 | Payment method | **Yes** — no payment = no booking | Stripe SDK |
| 8 | Preferences | No | `PUT /auth/update` |

Home unlocked after step 7.

---

## Detailer onboarding (10 steps)

| Step | Screen | Blocking | API |
|---|---|---|---|
| 1 | Splash — choose role | — | — |
| 2 | Identify + verify + complete profile | — | Identifier-first flow |
| 3 | Personal info + bio | No | `PUT /api/v1/detailers/me` |
| 4 | Service zone + radius | No | `PUT /api/v1/detailers/me` |
| 5 | Services + custom prices | No | `PATCH /api/v1/detailers/me/services/{id}` |
| 6 | Weekly availability | No | `PUT /api/v1/detailers/me` |
| 7 | Identity verification | **Yes** — required for payouts | Stripe Identity SDK |
| 8 | Bank account (Stripe Connect) | **Yes** — required for payouts | Stripe Connect SDK |
| 9 | Activate availability | No | `PATCH /api/v1/detailers/me/status` |
| 10 | Detailer dashboard | — | — |

---

## Environment variables

```bash
# frontend/.env.local
EXPO_PUBLIC_API_URL=http://localhost:8000

# Physical device: replace localhost with machine LAN IP
EXPO_PUBLIC_API_URL=http://192.168.1.XX:8000
```

---

## Key dependencies

| Package | Purpose |
|---|---|
| `@react-navigation/native-stack` | Stack navigator |
| `@react-navigation/bottom-tabs` | Tab navigator |
| `axios` | HTTP client with interceptors |
| `zustand` | Auth state (sync JWT for WS) |
| `expo-secure-store` | Encrypted token storage |
| `expo-local-authentication` | Biometric quick-unlock on splash |
| `expo-location` | GPS for detailer location push |
| `expo-auth-session` | OAuth2 (Google, Apple) |
| `expo-apple-authentication` | Apple Sign-In |
| `expo-notifications` | Push notification handling |
| `expo-device` | Required by `usePushNotifications` to detect physical device |
| `expo-haptics` | Tap feedback in shared `Button` |
| `expo-image` | Memory-efficient image rendering |
| `expo-linear-gradient` | LoadingScreen + accent surfaces |
| `expo-splash-screen` | Native splash control |
| `react-native-passkey` | WebAuthn passkey quick-unlock |
| `react-native-calendars` | Availability calendar UI |
| `react-native-paper` | UI components |
| `react-native-reanimated` + `react-native-worklets` | Animations |
| `@stripe/stripe-react-native` | Stripe payment + Identity |
| `lucide-react-native` | Icon set |

---

## Common pitfalls

- **Two Axios clients** — never use `apiClient` for `/auth` endpoints. 404 guaranteed.
- **WS auth via query param** — `?token=<jwt>`. WS connections cannot send `Authorization` header after handshake.
- **Prices are cents** — always integers. Display: `price_cents / 100`.
- **Timestamps are UTC** — format for display in user's local timezone.
- **VehicleSize is not sent by the client** — it's derived on the backend from `body_class`. Only send `body_class`.
- **ASAP vs date mode** — ASAP: sort by `distance ASC, rating DESC`. Date: sort by `rating DESC, distance ASC`.
- **Don't define inline buttons / status pills / empty states** — use `<Button>`, `<StatusBadge>`, `<EmptyState>` from `components/`. Sprint 9 standardized 50+ duplicated definitions; new inline copies regress the system.
- **Use semantic tokens, not hex literals** — `Colors.bg.*`, `Colors.textColor.*`, `Colors.border.*`, `Spacing`, `Radius`, `TypographyScale`. Hex literals exist only in legacy keys kept for backward compatibility.
- **`raycarwash_registration_path`** — SecureStore key set by `setRegistrationPath()` on the ProviderType screen; cleared by `clearAuthTokens()`. Used to remember whether the user picked "Detailer" or "Continue as client" across the onboarding flow.
- **LoadingScreen resume rules** — if only `onboarding_token` is present (no access token), it navigates to `ProviderType` so the user finishes onboarding without re-logging in. Biometric cancel falls back to the stored access token before sending them to Login.
