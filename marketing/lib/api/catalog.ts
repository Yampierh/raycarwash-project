import { apiClient } from "./client";

export type Service = {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  base_price_cents: number;
  base_duration_minutes: number;
  price_small: number;
  price_medium: number;
  price_large: number;
  price_xl: number;
  duration_small_minutes: number;
  duration_medium_minutes: number;
  duration_large_minutes: number;
  duration_xl_minutes: number;
  is_active: boolean;
  created_at: string;
};

export type Addon = {
  id: string;
  name: string;
  description?: string | null;
  price_cents: number;
  duration_minutes: number;
  is_active: boolean;
  created_at: string;
};

export async function listServices() {
  const res = await apiClient.get<Service[]>("/services");
  return res.data;
}

export async function listAddons() {
  const res = await apiClient.get<Addon[]>("/addons");
  return res.data;
}
