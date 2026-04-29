import { apiClient, authClient } from "./api";

// ─── Response types ───────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string | null;
  refresh_token: string | null;
  onboarding_token: string | null;
  roles: string[];
  onboarding_completed: boolean;
  next_step: string;
}

export interface SocialAuthResponse {
  is_new_user: boolean;
  onboarding_required: boolean;
  onboarding_token?: string;
  access_token?: string;
  refresh_token?: string;
  token_type: string;
  active_role?: string;
}

export interface WebAuthnBeginResponse {
  challenge_token: string;
  options: Record<string, unknown>;
}

export interface WebAuthnRegisterCompleteResponse {
  credential_id: string;
  device_name: string;
}

// ─── Kept for backward compatibility (VerifyResponse used by CompleteProfileScreen) ─

export interface VerifyResponse {
  access_token?: string;
  refresh_token?: string;
  is_new_user: boolean;
  temp_token?: string;
  needs_profile_completion: boolean;
  next_step: string;
  assigned_role?: string;
}

// ─── Email / Password ─────────────────────────────────────────────────────────

/**
 * Authenticate an existing user.
 * Backend: POST /auth/login  { email, password }
 */
export const loginWithEmail = async (
  email: string,
  password: string,
): Promise<LoginResponse> => {
  const response = await authClient.post<LoginResponse>("/login", {
    email: email.toLowerCase().trim(),
    password,
  });
  return response.data;
};

/**
 * Register a new account (email + password only).
 * Backend: POST /auth/register  { email, password }
 * Always returns onboarding_token — caller must navigate to CompleteProfile.
 */
export const registerWithEmail = async (
  email: string,
  password: string,
): Promise<LoginResponse> => {
  const response = await authClient.post<LoginResponse>("/register", {
    email: email.toLowerCase().trim(),
    password,
  });
  return response.data;
};

// ─── Token refresh (called by 401 interceptor in api.ts) ─────────────────────

export const refreshAccessToken = async (
  refreshToken: string,
): Promise<{ access_token: string; refresh_token: string }> => {
  const response = await authClient.post(
    `/refresh?refresh_token=${encodeURIComponent(refreshToken)}`,
  );
  return response.data;
};

// ─── Logout ───────────────────────────────────────────────────────────────────

export const logout = async (): Promise<void> => {
  const { clearAuthTokens } = await import("../utils/storage");
  await clearAuthTokens();
};

// ─── Social auth ──────────────────────────────────────────────────────────────

/**
 * Exchange a Google PKCE authorization code for a backend token pair.
 * Backend: POST /auth/google  { code, code_verifier, redirect_uri }
 */
export const loginWithGoogle = async (params: {
  code: string;
  code_verifier: string;
  redirect_uri: string;
}): Promise<SocialAuthResponse> => {
  const response = await authClient.post<SocialAuthResponse>("/google", params);
  return response.data;
};

/**
 * Exchange an Apple identity token for a backend token pair.
 * Backend: POST /auth/apple  { identity_token, full_name? }
 */
export const loginWithApple = async (
  identityToken: string,
  fullName?: string,
): Promise<SocialAuthResponse> => {
  const response = await authClient.post<SocialAuthResponse>("/apple", {
    identity_token: identityToken,
    full_name: fullName,
  });
  return response.data;
};

// ─── Password reset ───────────────────────────────────────────────────────────

/**
 * Request a password reset email.
 * Backend: POST /auth/password-reset  { email }
 * Always returns 200 (prevents user enumeration).
 */
export const requestPasswordReset = async (email: string): Promise<void> => {
  await authClient.post("/password-reset", {
    email: email.toLowerCase().trim(),
  });
};

// ─── Complete profile (onboarding) ────────────────────────────────────────────

/**
 * Complete user profile after registration.
 * Backend assigns role based on service_type — frontend never controls role.
 * service_type=undefined → "client"; service_type="detailer" → "detailer"
 */
export const completeProfile = async (payload: {
  full_name: string;
  phone_number?: string;
  service_type?: string;
}): Promise<VerifyResponse> => {
  const response = await authClient.put<VerifyResponse>("/complete-profile", payload);
  return response.data;
};

// ─── WebAuthn / FIDO2 Passkeys ────────────────────────────────────────────────

export const webAuthnRegisterBegin = async (): Promise<WebAuthnBeginResponse> => {
  const response = await authClient.post<WebAuthnBeginResponse>(
    "/webauthn/register/begin",
  );
  return response.data;
};

export const webAuthnRegisterComplete = async (
  challengeToken: string,
  credential: Record<string, unknown>,
  deviceName: string,
): Promise<WebAuthnRegisterCompleteResponse> => {
  const response = await authClient.post<WebAuthnRegisterCompleteResponse>(
    "/webauthn/register/complete",
    { challenge_token: challengeToken, credential, device_name: deviceName },
  );
  return response.data;
};

export const webAuthnAuthenticateBegin = async (
  email: string,
): Promise<WebAuthnBeginResponse> => {
  const response = await authClient.post<WebAuthnBeginResponse>(
    "/webauthn/authenticate/begin",
    { email: email.toLowerCase().trim() },
  );
  return response.data;
};

export const webAuthnAuthenticateComplete = async (
  challengeToken: string,
  credential: Record<string, unknown>,
): Promise<{ access_token: string; refresh_token: string }> => {
  const response = await authClient.post<{
    access_token: string;
    refresh_token: string;
  }>("/webauthn/authenticate/complete", {
    challenge_token: challengeToken,
    credential,
  });
  return response.data;
};

// ─── Identifier-first (kept for backward compatibility) ──────────────────────

export interface IdentifyResponse {
  identifier: string;
  identifier_type: "email" | "phone";
  exists: boolean;
  auth_methods: string[];
  is_new_user: boolean;
  suggested_action: string;
}

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

export const verify = async (
  identifier: string,
  identifierType: string,
  options: { password?: string; accessToken?: string; otpCode?: string },
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
