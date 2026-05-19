/**
 * marketing/lib/api/users-hub.ts
 *
 * Profile Hub client for /api/v1/users/me (ADR-002b). Mirrors the mobile
 * track's frontend/src/services/users.service.ts so types stay in sync.
 *
 * Adds:
 *   getHub(includes, options)  — typed read with HubResult { data, meta }
 *   updateProfile(body)        — PATCH /users/me, returns the updated Hub
 *
 * The legacy auth-client.ts at /auth/me + /auth/update is preserved for
 * pages not yet migrated. Each page can move independently.
 */
import { apiClient, unwrapWithMeta } from "./client";

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

export interface HubUserCore {
  id: string;
  email: string;
  email_verified: boolean;
  phone: string | null;
  phone_verified: boolean;
  role: string | null;
  available_roles: string[];
  created_at: string;
}

export interface HubVerificationBadges {
  email: boolean;
  phone: boolean;
  identity: boolean;
  background_check: boolean;
}

export interface HubProfileBlock {
  first_name: string | null;
  last_name: string | null;
  full_name: string | null;
  pronouns: string | null;
  avatar_url: string | null;
  cover_url: string | null;
  language: string;
  timezone: string;
}

export interface HubStatsBlock {
  total_bookings: number;
  total_spent_cents: number;
  favorite_provider_id: string | null;
  vehicles_total: number;
  favorites_total: number;
  member_since: string | null;
}

export interface HubSecurityBlock {
  has_password: boolean;
  two_factor_enabled: boolean;
  passkeys_count: number;
  last_password_change: string | null;
  last_login_at: string | null;
  step_up_required: boolean;
  active_sessions_count: number;
  recent_failed_attempts: number;
}

export interface HubSessionItem {
  id: string;
  device_name: string | null;
  user_agent: string | null;
  ip_address: string | null;
  ip_location: string | null;
  is_current: boolean;
  created_at: string;
  last_seen_at: string | null;
}

export interface HubProviderBlock {
  business_name: string | null;
  display_name: string | null;
  tagline: string | null;
  bio: string | null;
  verification_status: string;
  rating: number | null;
  total_jobs: number;
  is_accepting_bookings: boolean;
}

export interface HubVehicleSummary {
  id: string;
  make: string;
  model: string;
  year: number;
  color: string | null;
  license_plate: string | null;
  photo_url: string | null;
  is_default: boolean;
}

export interface HubAddressSummary {
  id: string;
  label: string | null;
  line1: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  is_default: boolean;
}

export interface HubPaymentMethodSummary {
  id: string;
  brand: string | null;
  last4: string | null;
  exp_month: number | null;
  exp_year: number | null;
  is_default: boolean;
}

export interface HubFavoriteProviderSummary {
  provider_user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  rating: number | null;
}

export interface HubPreferencesBlock {
  default_vehicle_id: string | null;
  default_address_id: string | null;
  marketing_opt_in: boolean;
  frequency_preference: string | null;
}

export interface HubNotificationsBlock {
  preferences: Record<string, Record<string, boolean>>;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
}

export interface HubData {
  user: HubUserCore;
  verification_badges: HubVerificationBadges;

  profile: HubProfileBlock | null;
  stats: HubStatsBlock | null;
  security: HubSecurityBlock | null;
  sessions: HubSessionItem[] | null;
  provider: HubProviderBlock | null;
  vehicles: HubVehicleSummary[] | null;
  addresses: HubAddressSummary[] | null;
  payment_methods: HubPaymentMethodSummary[] | null;
  favorites: HubFavoriteProviderSummary[] | null;
  preferences: HubPreferencesBlock | null;
  notifications: HubNotificationsBlock | null;
}

export interface HubMeta {
  includes?: string[];
  skipped_due_to_step_up?: string[];
}

export interface HubResult {
  data: HubData;
  meta: HubMeta;
}

export interface HubProfilePatch {
  first_name?: string;
  last_name?: string;
  pronouns?: string;
  language?: string;
  timezone?: string;
}

export interface GetHubOptions {
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

export async function updateProfile(body: HubProfilePatch): Promise<HubResult> {
  const response = await apiClient.patch("/users/me", body);
  const { data, meta } = unwrapWithMeta<HubData, HubMeta>(response);
  return { data, meta: meta ?? {} };
}
