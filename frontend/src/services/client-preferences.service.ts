/**
 * frontend/src/services/client-preferences.service.ts
 *
 * Wraps /api/v1/users/me/client-preferences (Phase 4 chunk V).
 *
 * PUT semantics — the body must include every field, not partial.
 * Backend validates default_vehicle_id / default_address_id are
 * caller-owned before writing.
 */
import { apiClient, unwrap } from "./api";

export interface ClientPreferences {
  default_vehicle_id: string | null;
  default_address_id: string | null;
  marketing_opt_in: boolean;
  frequency_preference: string | null;
}

export async function getClientPreferences(): Promise<ClientPreferences> {
  const res = await apiClient.get("/api/v1/users/me/client-preferences");
  return unwrap<ClientPreferences>(res);
}

export async function putClientPreferences(
  body: ClientPreferences,
): Promise<ClientPreferences> {
  const res = await apiClient.put("/api/v1/users/me/client-preferences", body);
  return unwrap<ClientPreferences>(res);
}
