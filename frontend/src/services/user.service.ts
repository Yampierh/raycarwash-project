import { authClient } from "./api";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  phone_number: string | null;
  role: "client" | "detailer" | "admin";
  is_active: boolean;
  is_verified: boolean;
  service_address?: string | null;
  created_at: string;
  updated_at: string;
}

export const getUserProfile = async (): Promise<UserProfile> => {
  const response = await authClient.get("/me");
  return response.data;
};

export const updateUserProfile = async (userData: {
  full_name: string;
  phone_number?: string;
  service_address?: string;
}): Promise<UserProfile> => {
  const response = await authClient.put("/update", userData);
  return response.data;
};
