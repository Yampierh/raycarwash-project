import axios, { AxiosInstance } from "axios";
import { useAuthStore } from "@/lib/store/auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const authClient: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/auth`,
});

// Inject access_token if present, else onboarding_token (needed for /complete-profile).
authClient.interceptors.request.use((config) => {
  const { accessToken, onboardingToken } = useAuthStore.getState();
  const token = accessToken ?? onboardingToken;
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Typed auth API helpers ---

export type LoginResponse = {
  access_token?: string;
  refresh_token?: string;
  onboarding_token?: string;
  roles?: string[];
  next_step?: "complete_profile" | "detailer_onboarding" | "ready";
  onboarding_completed?: boolean;
};

export type SocialAuthResponse = {
  is_new_user: boolean;
  access_token?: string;
  refresh_token?: string;
  onboarding_token?: string;
  roles?: string[];
  next_step?: "complete_profile" | "detailer_onboarding" | "ready";
};

export type CompleteProfileRequest = {
  full_name: string;
  phone_number: string;
  service_type?: "detailer" | null;
};

export type UserRead = {
  id: string;
  email: string;
  full_name?: string;
  phone_number?: string;
  service_type?: "detailer" | null;
  is_active?: boolean;
};

export async function register(email: string, password: string) {
  const res = await authClient.post<LoginResponse>("/register", {
    email,
    password,
  });
  return res.data;
}

export async function login(email: string, password: string) {
  const res = await authClient.post<LoginResponse>("/login", {
    email,
    password,
  });
  return res.data;
}

export async function completeProfile(body: CompleteProfileRequest) {
  const res = await authClient.put<LoginResponse>("/complete-profile", body);
  return res.data;
}

export async function googleLogin(args: {
  code: string;
  code_verifier: string;
  redirect_uri: string;
}) {
  const res = await authClient.post<SocialAuthResponse>("/google", args);
  return res.data;
}

export async function me() {
  const res = await authClient.get<UserRead>("/me");
  return res.data;
}

export async function logout(refresh_token: string) {
  await authClient.post("/logout", { refresh_token });
}
