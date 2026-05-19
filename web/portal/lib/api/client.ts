import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "@/lib/store/auth";
import { ApiError, StepUpRequiredError, toApiError } from "./api-error";

export { ApiError, StepUpRequiredError };
export type { ApiErrorPayload, ApiErrorMeta } from "./api-error";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
});

apiClient.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState();
  if (accessToken) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// --- 401 refresh handling ---

type Resolver = (token: string | null) => void;
let refreshing: Promise<string | null> | null = null;
let waiters: Resolver[] = [];

function notifyWaiters(token: string | null) {
  waiters.forEach((w) => w(token));
  waiters = [];
}

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, setSession, clear } = useAuthStore.getState();
  if (!refreshToken) {
    clear();
    return null;
  }
  try {
    const res = await axios.post(
      `${BASE_URL}/auth/refresh`,
      null,
      { params: { refresh_token: refreshToken } }
    );
    const data = res.data as {
      access_token: string;
      refresh_token: string;
    };
    setSession({
      access_token: data.access_token,
      refresh_token: data.refresh_token,
    });
    return data.access_token;
  } catch {
    clear();
    return null;
  }
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;

    // Detect step-up first — surfaces a re-auth modal, not a refresh attempt.
    const envelopeError = toApiError(error.response?.data, error.response?.status ?? 0);
    if (envelopeError instanceof StepUpRequiredError) {
      return Promise.reject(envelopeError);
    }

    if (!original || error.response?.status !== 401 || original._retry) {
      if (envelopeError) return Promise.reject(envelopeError);
      return Promise.reject(error);
    }
    original._retry = true;

    if (!refreshing) {
      refreshing = refreshAccessToken().finally(() => {
        refreshing = null;
      });
      const token = await refreshing;
      notifyWaiters(token);
      if (!token) {
        if (typeof window !== "undefined") window.location.href = "/login";
        return Promise.reject(envelopeError ?? error);
      }
      original.headers = original.headers ?? {};
      original.headers.Authorization = `Bearer ${token}`;
      return apiClient(original);
    }

    return new Promise((resolve, reject) => {
      waiters.push((token) => {
        if (!token) {
          if (typeof window !== "undefined") window.location.href = "/login";
          reject(envelopeError ?? error);
          return;
        }
        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${token}`;
        apiClient(original).then(resolve, reject);
      });
    });
  }
);

/** Unwrap `{data, meta, links}` envelopes returned by /api/v1/* endpoints. */
export function unwrap<T>(response: { data: { data: T } }): T {
  return response.data.data;
}

/** Same as unwrap() but keeps meta + links — useful for paginated lists. */
export function unwrapWithMeta<T, M = Record<string, unknown>>(
  response: { data: { data: T; meta?: M; links?: Record<string, string> } },
): { data: T; meta: M | undefined; links: Record<string, string> | undefined } {
  return {
    data: response.data.data,
    meta: response.data.meta,
    links: response.data.links,
  };
}
