import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { APP_CONFIG } from "../config/app.config";
import { ApiError, StepUpRequiredError, toApiError } from "../lib/api-error";
import { navigationRef } from "../navigation/navigationRef";
import {
  clearAuthTokens,
  getOnboardingToken,
  getRefreshToken,
  getToken,
  saveRefreshToken,
  saveToken,
} from "../utils/storage";
import { refreshAccessToken } from "./auth.service";

export { ApiError, StepUpRequiredError };
export type { ApiErrorPayload, ApiErrorMeta } from "../lib/api-error";

const SERVER_URL = process.env.EXPO_PUBLIC_API_URL || APP_CONFIG.apiBaseUrl;

/**
 * WebSocket base URL — replaces http(s):// with ws(s)://.
 * Usage: `new WebSocket(\`${WS_BASE_URL}/ws/appointments/${id}?token=${token}\`)`
 */
export const WS_BASE_URL = SERVER_URL.replace(/^http/, "ws");

// 1. Instancias
export const authClient = axios.create({
  baseURL: `${SERVER_URL}/auth`,
  headers: { "Content-Type": "application/json" },
  timeout: 10000,
});

export const apiClient = axios.create({
  baseURL: `${SERVER_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: 10000,
});

// 2. Inyección de token
// apiClient (resto de la API): SOLO access token. Nunca onboarding scope.
// authClient (/auth/*): access token con fallback a onboarding token, para que
// PUT /auth/complete-profile pueda llamarse durante el onboarding.
const injectAccessToken = async (config: InternalAxiosRequestConfig) => {
  const token = await getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

const injectAuthToken = async (config: InternalAxiosRequestConfig) => {
  const token = (await getToken()) ?? (await getOnboardingToken());
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

authClient.interceptors.request.use(injectAuthToken, (error) =>
  Promise.reject(error),
);
apiClient.interceptors.request.use(injectAccessToken, (error) =>
  Promise.reject(error),
);

// --- Lógica de Refresh Token (Solo para apiClient) ---
// Normalmente no quieres refresh automático en /auth para evitar bucles infinitos
let _isRefreshing = false;
let _pendingRequests: Array<(newToken: string) => void> = [];

function onTokenRefreshed(newToken: string) {
  _pendingRequests.forEach((resolve) => resolve(newToken));
  _pendingRequests = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Step-up is the FIRST thing to detect: the access token is fine, the user
    // is authenticated, but the endpoint needs re-auth ≤ STEP_UP_TTL_MINUTES.
    // Promote it to StepUpRequiredError so the UI can open the re-auth modal
    // without burning a refresh attempt.
    const envelopeError = toApiError(error.response?.data, error.response?.status ?? 0);
    if (envelopeError instanceof StepUpRequiredError) {
      return Promise.reject(envelopeError);
    }

    if (error.response?.status !== 401 || originalRequest._retry) {
      // Bare 4xx/5xx with our envelope shape — surface the typed error so
      // callers can `instanceof ApiError` and inspect `.code` / `.details`.
      if (envelopeError) return Promise.reject(envelopeError);
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    if (_isRefreshing) {
      return new Promise((resolve) => {
        _pendingRequests.push((newToken: string) => {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          resolve(apiClient(originalRequest));
        });
      });
    }

    _isRefreshing = true;

    try {
      const storedRefreshToken = await getRefreshToken();
      if (!storedRefreshToken) throw new Error("No refresh token available");

      const tokens = await refreshAccessToken(storedRefreshToken);

      await saveToken(tokens.access_token);
      await saveRefreshToken(tokens.refresh_token);

      onTokenRefreshed(tokens.access_token);

      originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
      return apiClient(originalRequest);
    } catch {
      _pendingRequests = [];
      await clearAuthTokens();
      if (navigationRef.isReady()) {
        navigationRef.reset({ index: 0, routes: [{ name: "Login" }] });
      }
      return Promise.reject(envelopeError ?? error);
    } finally {
      _isRefreshing = false;
    }
  },
);

/**
 * Unwrap an envelope `{data, meta, links}` returned by /api/v1/* endpoints.
 * Returns `data` directly for callers that don't need meta/links. New
 * services should prefer importing this helper instead of reaching into
 * `response.data.data` by hand.
 */
export function unwrap<T>(response: { data: { data: T } }): T {
  return response.data.data;
}

/**
 * Same as unwrap() but keeps `meta` (cursor pagination, includes, step-up
 * info). Use for list endpoints and the Profile Hub `/users/me`.
 */
export function unwrapWithMeta<T, M = Record<string, unknown>>(
  response: { data: { data: T; meta?: M; links?: Record<string, string> } },
): { data: T; meta: M | undefined; links: Record<string, string> | undefined } {
  return {
    data: response.data.data,
    meta: response.data.meta,
    links: response.data.links,
  };
}
