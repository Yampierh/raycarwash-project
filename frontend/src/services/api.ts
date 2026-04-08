import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { APP_CONFIG } from "../config/app.config";
import { navigationRef } from "../navigation/navigationRef";
import {
  clearAuthTokens,
  getRefreshToken,
  getToken,
  saveRefreshToken,
  saveToken,
} from "../utils/storage";
import { refreshAccessToken } from "./auth.service";

const SERVER_URL = process.env.EXPO_PUBLIC_API_URL || APP_CONFIG.apiBaseUrl;

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

// 2. Función lógica para inyectar Token (Reutilizable)
const injectToken = async (config: InternalAxiosRequestConfig) => {
  const token = await getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

// 3. Aplicar interceptor de petición a AMBAS instancias
// Importante: authClient lo necesita para el endpoint /me
authClient.interceptors.request.use(injectToken, (error) =>
  Promise.reject(error),
);
apiClient.interceptors.request.use(injectToken, (error) =>
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

    if (error.response?.status !== 401 || originalRequest._retry) {
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
      return Promise.reject(error);
    } finally {
      _isRefreshing = false;
    }
  },
);
