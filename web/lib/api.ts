import axios, { AxiosInstance } from "axios";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
} from "./auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api: AxiosInstance = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = getRefreshToken();
      if (refresh) {
        try {
          const res = await axios.post(`${BASE_URL}/auth/refresh`, null, {
            params: { refresh_token: refresh },
          });
          const { access_token, refresh_token } = res.data;
          saveTokens(access_token, refresh_token);
          original.headers.Authorization = `Bearer ${access_token}`;
          return api(original);
        } catch {
          clearTokens();
          window.location.href = "/login";
        }
      } else {
        clearTokens();
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ── Typed API helpers ───────────────────────────────────────────── //

export async function login(email: string, password: string) {
  const res = await axios.post(`${BASE_URL}/auth/login`, { email, password });
  return res.data as {
    access_token?: string;
    refresh_token?: string;
    roles: string[];
    onboarding_completed: boolean;
  };
}

export async function getStats() {
  const res = await api.get("/api/v1/admin/stats");
  return res.data;
}

export async function listUsers(params: {
  page?: number;
  per_page?: number;
  search?: string;
  role?: string;
}) {
  const res = await api.get("/api/v1/admin/users", { params });
  return res.data;
}

export async function getUser(id: string) {
  const res = await api.get(`/api/v1/admin/users/${id}`);
  return res.data;
}

export async function updateUser(id: string, body: { is_active?: boolean }) {
  const res = await api.patch(`/api/v1/admin/users/${id}`, body);
  return res.data;
}

export async function assignRole(userId: string, roleId: string) {
  const res = await api.post(`/api/v1/admin/users/${userId}/roles`, {
    role_id: roleId,
  });
  return res.data;
}

export async function revokeRole(userId: string, roleId: string) {
  await api.delete(`/api/v1/admin/users/${userId}/roles/${roleId}`);
}

export async function listRoles() {
  const res = await api.get("/api/v1/admin/roles");
  return res.data;
}

export async function createRole(body: { name: string; description?: string }) {
  const res = await api.post("/api/v1/admin/roles", body);
  return res.data;
}

export async function deleteRole(id: string) {
  await api.delete(`/api/v1/admin/roles/${id}`);
}

export async function listPermissions() {
  const res = await api.get("/api/v1/admin/permissions");
  return res.data;
}

export async function createPermission(body: {
  name: string;
  resource: string;
  action: string;
  description?: string;
}) {
  const res = await api.post("/api/v1/admin/permissions", body);
  return res.data;
}

export async function deletePermission(id: string) {
  await api.delete(`/api/v1/admin/permissions/${id}`);
}

export async function assignPermissionToRole(
  roleId: string,
  permissionId: string
) {
  await api.post(`/api/v1/admin/roles/${roleId}/permissions`, {
    permission_id: permissionId,
  });
}

export async function revokePermissionFromRole(
  roleId: string,
  permissionId: string
) {
  await api.delete(
    `/api/v1/admin/roles/${roleId}/permissions/${permissionId}`
  );
}
