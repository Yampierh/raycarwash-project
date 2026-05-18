/**
 * frontend/src/services/favorites.service.ts
 *
 * Wraps /api/v1/users/me/favorites/providers (Phase 4 chunk V).
 *
 * Add/remove are idempotent at the backend (ON CONFLICT DO NOTHING for
 * add, no-op-friendly DELETE for remove), so the UI can tap-tap without
 * special-casing.
 */
import { apiClient, unwrap } from "./api";

export interface FavoriteProvider {
  provider_user_id: string;
  display_name: string | null;
  business_name: string | null;
  avatar_url: string | null;
  rating: number | null;
  created_at: string;
}

export async function listFavorites(): Promise<FavoriteProvider[]> {
  const res = await apiClient.get("/api/v1/users/me/favorites/providers");
  return unwrap<FavoriteProvider[]>(res);
}

export async function addFavorite(providerUserId: string): Promise<FavoriteProvider> {
  const res = await apiClient.post(
    `/api/v1/users/me/favorites/providers/${providerUserId}`,
  );
  return unwrap<FavoriteProvider>(res);
}

export async function removeFavorite(providerUserId: string): Promise<void> {
  await apiClient.delete(
    `/api/v1/users/me/favorites/providers/${providerUserId}`,
  );
}
