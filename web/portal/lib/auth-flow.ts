import type { LoginResponse, SocialAuthResponse } from "@/lib/api/auth-client";
import type { ActiveRole, RoleIntent } from "@/lib/store/auth";

const SIGNUP_ROLE_KEY = "raycarwash_signup_role";

export type SignupRole = "client" | "detailer";

export function saveSignupRole(role: SignupRole) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(SIGNUP_ROLE_KEY, role);
}

export function getSignupRole(): SignupRole | null {
  if (typeof window === "undefined") return null;
  const v = sessionStorage.getItem(SIGNUP_ROLE_KEY);
  return v === "client" || v === "detailer" ? v : null;
}

export function clearSignupRole() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(SIGNUP_ROLE_KEY);
}

/**
 * Pick the activeRole to commit to the session after a successful auth.
 * - admin role overrides everything (admins always land in the admin dashboard).
 * - if the user has the chosen intent, use it.
 * - if the user has exactly one role, use that role (intent doesn't apply).
 * - else null (caller should redirect to /login with a clear error).
 */
export function resolveActiveRole(
  roles: string[],
  intent: RoleIntent | null
): ActiveRole | null {
  if (roles.includes("admin")) return "admin";
  const pref: RoleIntent = intent ?? "client";
  if (roles.includes(pref)) return pref;
  if (roles.length === 1) {
    const only = roles[0];
    if (only === "client" || only === "detailer" || only === "admin") {
      return only;
    }
  }
  return null;
}

/**
 * Decide where to send the user after an auth event (login, register, social).
 * Returns a path relative to the locale (consumed by next-intl router.push).
 */
export function resolvePostAuthPath(
  data: LoginResponse | SocialAuthResponse
): { path: string; externalAdmin?: boolean } {
  const access = data.access_token;
  const next = data.next_step;
  const roles = data.roles ?? [];

  if (next === "complete_profile" || (data.onboarding_token && !access)) {
    return { path: "/onboarding" };
  }

  if (roles.includes("admin")) {
    return { path: "/dashboard", externalAdmin: true };
  }

  if (next === "detailer_onboarding") {
    return { path: "/onboarding/detailer" };
  }

  return { path: "/dashboard" };
}
