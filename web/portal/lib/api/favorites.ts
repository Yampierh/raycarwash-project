import { apiClient, unwrap } from "./client";

export type FavoriteProvider = {
  provider_user_id: string;
  display_name: string | null;
  business_name: string | null;
  avatar_url: string | null;
  rating: number | null;
  created_at: string;
};

export async function listFavorites(): Promise<FavoriteProvider[]> {
  const res = await apiClient.get("/users/me/favorites/providers");
  return unwrap<FavoriteProvider[]>(res);
}

export async function removeFavorite(providerUserId: string): Promise<void> {
  await apiClient.delete(`/users/me/favorites/providers/${providerUserId}`);
}
