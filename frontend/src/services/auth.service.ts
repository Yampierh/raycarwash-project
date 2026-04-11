import { apiClient, authClient } from "./api";

export interface CheckEmailResponse {
  email: string;
  exists: boolean;
  auth_method: "password" | "google" | "apple" | "both" | "none";
  suggested_action: "login" | "social_login" | "register";
}

export interface IdentifyResponse {
  identifier: string;
  identifier_type: "email" | "phone";
  exists: boolean;
  auth_methods: string[];
  is_new_user: boolean;
  suggested_action: string;
}

export interface VerifyResponse {
  access_token?: string;
  refresh_token?: string;
  is_new_user: boolean;
  temp_token?: string;
  needs_profile_completion: boolean;
  next_step: string;
  assigned_role?: string;
}

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
  email: string;
  password: string;
  full_name?: string;
  phone_number?: string;
  role_names?: string[];
}) => {
  const response = await apiClient.post("/users", {
    ...payload,
    email: payload.email.toLowerCase().trim(),
    role_names: payload.role_names ?? ["client"],
    full_name: payload.full_name || "User",
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

// ─── Check email exists ────────────────────────────────────────────────────────

/**
 * Check if an email is registered and get auth method.
 * Backend endpoint: POST /auth/check-email  { email: string }
 * NOTE: Uses authClient (base: /auth) not apiClient (base: /api/v1)
 */
export const checkEmail = async (
  email: string,
): Promise<CheckEmailResponse> => {
  const response = await authClient.post<CheckEmailResponse>("/check-email", {
    email: email.toLowerCase().trim(),
  });
  return response.data;
};

// ─── Identifier-First Auth ────────────────────────────────────────────────

/**
 * Identify user by email or phone.
 * Backend endpoint: POST /auth/identify
 */
export const identify = async (
  identifier: string,
  identifierType?: string,
): Promise<IdentifyResponse> => {
  const response = await authClient.post<IdentifyResponse>("/identify", {
    identifier: identifier.toLowerCase().trim(),
    identifier_type: identifierType || null,
  });
  return response.data;
};

/**
 * Verify credentials in Identifier-First flow.
 * Backend endpoint: POST /auth/verify
 */
export const verify = async (
  identifier: string,
  identifierType: string,
  options: {
    password?: string;
    accessToken?: string;
    otpCode?: string;
  },
): Promise<VerifyResponse> => {
  const response = await authClient.post<VerifyResponse>("/verify", {
    identifier,
    identifier_type: identifierType,
    password: options.password || null,
    access_token: options.accessToken || null,
    otp_code: options.otpCode || null,
  });
  return response.data;
};

/**
 * Complete user profile after registration.
 * Backend endpoint: PUT /auth/complete-profile
 */
export const completeProfile = async (
  tempToken: string,
  payload: {
    full_name: string;
    phone_number?: string;
    role: string;
  },
): Promise<VerifyResponse> => {
  const response = await authClient.put<VerifyResponse>("/complete-profile", payload, {
    headers: { "X-Temp-Token": tempToken },
  });
  return response.data;
};
