/**
 * frontend/src/services/users.service.ts
 *
 * Profile Hub client for /api/v1/users/me (ADR-002b). Mirrors the
 * `domains/users/hub_schemas.py` shapes.
 *
 * `getHub(includes, options)` builds the URL, attaches `?on_step_up=skip`
 * when requested, and unwraps the `{data, meta, links}` envelope into a
 * `HubResult` containing both the typed payload and the meta block (so the
 * caller can react to `meta.skipped_due_to_step_up`).
 *
 * The legacy `user.service.ts` (singular) still talks to `/auth/me` for
 * screens not yet migrated to React Query. Both can coexist during the
 * deprecation window.
 */
import { apiClient, unwrapWithMeta } from "./api";

// ─── Token whitelist (mirrors backend include_spec.ALL_TOKENS) ───────────────

export type HubInclude =
  | "profile"
  | "stats"
  | "preferences"
  | "notifications"
  | "vehicles"
  | "addresses"
  | "payment_methods"
  | "favorites"
  | "provider"
  | "security"
  | "sessions";

// ─── Block types (mirror backend hub_schemas.py) ─────────────────────────────

export interface UserCore {
  id: string;
  email: string;
  email_verified: boolean;
  phone: string | null;
  phone_verified: boolean;
  role: string | null;
  available_roles: string[];
  created_at: string;
}

export interface VerificationBadges {
  email: boolean;
  phone: boolean;
  identity: boolean;
  background_check: boolean;
}

export interface ProfileBlock {
  first_name: string | null;
  last_name: string | null;
  full_name: string | null;
  pronouns: string | null;
  avatar_url: string | null;
  cover_url: string | null;
  language: string;
  timezone: string;
}

export interface StatsBlock {
  total_bookings: number;
  total_spent_cents: number;
  favorite_provider_id: string | null;
  vehicles_total: number;
  favorites_total: number;
  member_since: string | null;
}

export interface SecurityBlock {
  has_password: boolean;
  two_factor_enabled: boolean;
  passkeys_count: number;
  last_password_change: string | null;
  last_login_at: string | null;
  step_up_required: boolean;
  active_sessions_count: number;
  recent_failed_attempts: number;
}

export interface SessionItem {
  id: string;
  device_name: string | null;
  user_agent: string | null;
  ip_address: string | null;
  ip_location: string | null;
  is_current: boolean;
  created_at: string;
  last_seen_at: string | null;
}

export interface ProviderBlock {
  business_name: string | null;
  display_name: string | null;
  tagline: string | null;
  bio: string | null;
  verification_status: string;
  rating: number | null;
  total_jobs: number;
  is_accepting_bookings: boolean;
}

export interface VehicleSummary {
  id: string;
  make: string;
  model: string;
  year: number;
  color: string | null;
  license_plate: string | null;
  photo_url: string | null;
  is_default: boolean;
}

export interface AddressSummary {
  id: string;
  label: string | null;
  line1: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  is_default: boolean;
}

export interface PaymentMethodSummary {
  id: string;
  brand: string | null;
  last4: string | null;
  exp_month: number | null;
  exp_year: number | null;
  is_default: boolean;
}

export interface FavoriteProviderSummary {
  provider_user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  rating: number | null;
}

export interface PreferencesBlock {
  default_vehicle_id: string | null;
  default_address_id: string | null;
  marketing_opt_in: boolean;
  frequency_preference: string | null;
}

export interface NotificationsBlock {
  preferences: Record<string, Record<string, boolean>>;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
}

export interface HubData {
  user: UserCore;
  verification_badges: VerificationBadges;

  profile: ProfileBlock | null;
  stats: StatsBlock | null;
  security: SecurityBlock | null;
  sessions: SessionItem[] | null;
  provider: ProviderBlock | null;
  vehicles: VehicleSummary[] | null;
  addresses: AddressSummary[] | null;
  payment_methods: PaymentMethodSummary[] | null;
  favorites: FavoriteProviderSummary[] | null;
  preferences: PreferencesBlock | null;
  notifications: NotificationsBlock | null;
}

export interface HubMeta {
  includes?: string[];
  skipped_due_to_step_up?: string[];
}

export interface HubResult {
  data: HubData;
  meta: HubMeta;
}

// ─── Request body for PATCH /users/me ────────────────────────────────────────

export interface UpdateProfileBody {
  first_name?: string;
  last_name?: string;
  pronouns?: string;
  language?: string; // BCP-47, e.g. "en", "en-US", "es"
  timezone?: string; // IANA, e.g. "America/Indiana/Indianapolis"
}

// ─── Service functions ───────────────────────────────────────────────────────

export interface GetHubOptions {
  /** When the call needs sensitive blocks but step-up isn't recent, the
   * server returns 401 by default. Pass `skipStepUp=true` to receive 200
   * with those blocks omitted and `meta.skipped_due_to_step_up` set. */
  skipStepUp?: boolean;
}

export async function getHub(
  includes: HubInclude[] = [],
  options: GetHubOptions = {},
): Promise<HubResult> {
  const params: Record<string, string> = {};
  if (includes.length > 0) params.include = includes.join(",");
  if (options.skipStepUp) params.on_step_up = "skip";

  const response = await apiClient.get("/users/me", { params });
  const { data, meta } = unwrapWithMeta<HubData, HubMeta>(response);
  return { data, meta: meta ?? {} };
}

export async function updateProfile(body: UpdateProfileBody): Promise<HubResult> {
  const response = await apiClient.patch("/users/me", body);
  const { data, meta } = unwrapWithMeta<HubData, HubMeta>(response);
  return { data, meta: meta ?? {} };
}
