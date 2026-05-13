import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";
import { useAuthStore } from "@/lib/store/auth";

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
    if (!original || error.response?.status !== 401 || original._retry) {
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
        return Promise.reject(error);
      }
      original.headers = original.headers ?? {};
      original.headers.Authorization = `Bearer ${token}`;
      return apiClient(original);
    }

    return new Promise((resolve, reject) => {
      waiters.push((token) => {
        if (!token) {
          if (typeof window !== "undefined") window.location.href = "/login";
          reject(error);
          return;
        }
        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${token}`;
        apiClient(original).then(resolve, reject);
      });
    });
  }
);
