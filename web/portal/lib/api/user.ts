import { authClient } from "./auth-client";

export type Me = {
  id: string;
  email: string;
  full_name?: string | null;
  phone_number?: string | null;
  service_type?: "detailer" | null;
  is_active?: boolean;
  created_at?: string;
};

export type UserUpdate = {
  full_name?: string;
  phone_number?: string;
};

export async function getMe() {
  const res = await authClient.get<Me>("/me");
  return res.data;
}

export async function updateMe(body: UserUpdate) {
  const res = await authClient.put<Me>("/update", body);
  return res.data;
}
