import { apiClient } from "./api";

export interface Addon {
  id: string;
  name: string;
  description: string | null;
  price_cents: number;
  duration_minutes: number;
  is_active: boolean;
  created_at: string;
}

/**
 * GET /api/v1/addons
 * Public catalog of add-on extras (no auth required).
 */
export const getAddons = async (): Promise<Addon[]> => {
  const response = await apiClient.get("/addons");
  return response.data;
};
