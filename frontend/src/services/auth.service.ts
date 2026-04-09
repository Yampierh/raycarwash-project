import { apiClient, authClient } from "./api";

// ─── Logout ──────────────────────────────────────────────────────────────────

export const logout = async (): Promise<void> => {
  const { clearAuthTokens } = await import("../utils/storage");
  await clearAuthTokens();
};

// ─── Email / Password ────────────────────────────────────────────────────────

export const loginWithBackend = async (email: string, password: string) => {
  const params = new URLSearchParams();
  params.append("username", email.toLowerCase().trim());
  params.append("password", password);

  // ANTES: "/auth/token" -> AHORA: "/token"
  const response = await authClient.post("/token", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return response.data;
};

export const registerUser = async (payload: {
  full_name: string;
  email: string;
  password: string;
  phone_number?: string;
  role_names?: string[];  // e.g., ["client"], ["detailer"], or ["client", "detailer"]
}) => {
  const response = await apiClient.post("/users", {
    ...payload,
    email: payload.email.toLowerCase().trim(),
    role_names: payload.role_names ?? ["client"],
  });
  return response.data;
};

// ─── Token refresh (called by 401 interceptor in api.ts) ─────────────────────

export const refreshAccessToken = async (
  refreshToken: string,
): Promise<{ access_token: string; refresh_token: string }> => {
  // Backend expects query parameter, not JSON body
  const response = await authClient.post(
    `/refresh?refresh_token=${encodeURIComponent(refreshToken)}`,
  );
  return response.data;
};

// ─── Social auth (requires backend endpoints /auth/google and /auth/apple) ───

/**
 * Exchange a Google OAuth access token for a backend JWT pair.
 * Backend endpoint: POST /auth/google  { access_token: string }
 * NOTE: Uses authClient (base: /auth) not apiClient (base: /api/v1)
 */
export const loginWithGoogle = async (
  accessToken: string,
): Promise<{ access_token: string; refresh_token: string }> => {
  const response = await authClient.post("/google", {
    access_token: accessToken,
  });
  return response.data;
};

/**
 * Exchange an Apple identity token for a backend JWT pair.
 * Backend endpoint: POST /auth/apple  { identity_token: string, full_name?: string }
 * NOTE: Uses authClient (base: /auth) not apiClient (base: /api/v1)
 */
export const loginWithApple = async (
  identityToken: string,
  fullName?: string,
): Promise<{ access_token: string; refresh_token: string }> => {
  const response = await authClient.post("/apple", {
    identity_token: identityToken,
    full_name: fullName,
  });
  return response.data;
};

// ─── Password reset ───────────────────────────────────────────────────────────

/**
 * Request a password reset email.
 * Backend endpoint: POST /auth/password-reset  { email: string }
 * NOTE: Uses authClient (base: /auth) not apiClient (base: /api/v1)
 */
export const requestPasswordReset = async (email: string): Promise<void> => {
  await authClient.post("/password-reset", {
    email: email.toLowerCase().trim(),
  });
};
