import type { LoginResponse, SocialAuthResponse } from "@/lib/api/auth-client";
import { extractRole } from "@/lib/auth";

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
 * Decide where to send the user after an auth event (login, register, social).
 * Returns a path relative to the locale (consumed by next-intl router.push).
 */
export function resolvePostAuthPath(
  data: LoginResponse | SocialAuthResponse
): { path: string; externalAdmin?: boolean } {
  const access = data.access_token;
  const next = data.next_step;
  const role = access ? extractRole(access) : null;

  if (next === "complete_profile" || (data.onboarding_token && !access)) {
    return { path: "/onboarding" };
  }

  if (role === "admin") {
    return { path: "/dashboard", externalAdmin: true };
  }

  if (next === "detailer_onboarding") {
    return { path: "/onboarding/detailer" };
  }

  return { path: "/dashboard" };
}
