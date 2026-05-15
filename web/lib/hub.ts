/**
 * web/lib/hub.ts
 *
 * Profile Hub client for the admin web. Mirrors the mobile and marketing
 * tracks (frontend/src/services/users.service.ts and
 * marketing/lib/api/users-hub.ts) so the type shapes stay in lockstep
 * across all three frontends.
 *
 * Scope:
 *   - The admin's OWN profile via `/api/v1/users/me` (used by an admin
 *     self-profile page when we add one).
 *   - Other users' Hub data is NOT exposed by /api/v1/admin/users/{id}
 *     today — that endpoint returns a different shape. Phase 5 of the
 *     plan adds `GET /api/v1/admin/users/{id}/hub` (or extends the
 *     existing admin user detail endpoint to include hub blocks); when
 *     that lands, point `getUserHubAsAdmin` below at it.
 */
import { api, unwrap, unwrapWithMeta } from "./api";

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

export interface HubData {
  user: HubUserCore;
  verification_badges: HubVerificationBadges;
  profile: HubProfileBlock | null;
  stats: HubStatsBlock | null;
  security: HubSecurityBlock | null;
  provider: HubProviderBlock | null;
  sessions: unknown[] | null;
  vehicles: unknown[] | null;
  addresses: unknown[] | null;
  payment_methods: unknown[] | null;
  favorites: unknown[] | null;
  preferences: unknown | null;
  notifications: unknown | null;
}

export interface HubMeta {
  includes?: string[];
  skipped_due_to_step_up?: string[];
}

export interface HubResult {
  data: HubData;
  meta: HubMeta;
}

export interface GetHubOptions {
  skipStepUp?: boolean;
}

/** Fetch the CURRENT admin's Profile Hub. */
export async function getMyHub(
  includes: HubInclude[] = [],
  options: GetHubOptions = {},
): Promise<HubResult> {
  const params: Record<string, string> = {};
  if (includes.length > 0) params.include = includes.join(",");
  if (options.skipStepUp) params.on_step_up = "skip";
  const response = await api.get("/api/v1/users/me", { params });
  const { data, meta } = unwrapWithMeta<HubData, HubMeta>(response);
  return { data, meta: meta ?? {} };
}

export interface HubProfilePatch {
  first_name?: string;
  last_name?: string;
  pronouns?: string;
  language?: string;
  timezone?: string;
}

export async function patchMyHub(body: HubProfilePatch): Promise<HubResult> {
  const response = await api.patch("/api/v1/users/me", body);
  const { data, meta } = unwrapWithMeta<HubData, HubMeta>(response);
  return { data, meta: meta ?? {} };
}

/**
 * Placeholder for the admin endpoint that will return any user's Hub
 * (Phase 5 of the plan). Throws until backend ships
 * `GET /api/v1/admin/users/{id}/hub` (or equivalent). Call sites can
 * already be typed against this signature so the migration is mechanical
 * once the backend lands.
 */
export async function getUserHubAsAdmin(
  _userId: string,
  _includes: HubInclude[] = [],
): Promise<HubResult> {
  throw new Error(
    "getUserHubAsAdmin: admin Hub proxy endpoint not implemented yet. " +
      "Pending Phase 5 — see ADR-001 + admin endpoints in the Profile plan.",
  );
}

// Keep the unwrap helper exported so other admin pages can import a typed
// signature from one place.
export { unwrap };
