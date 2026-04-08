import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "raycarwash_jwt_token";
const REFRESH_TOKEN_KEY = "raycarwash_refresh_token";

// --- Access token ---

export const saveToken = async (token: string): Promise<void> => {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
};

export const getToken = async (): Promise<string | null> => {
  return await SecureStore.getItemAsync(TOKEN_KEY);
};

export const removeToken = async (): Promise<void> => {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
};

// --- Refresh token ---

export const saveRefreshToken = async (token: string): Promise<void> => {
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
};

export const getRefreshToken = async (): Promise<string | null> => {
  return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
};

export const removeRefreshToken = async (): Promise<void> => {
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
};

// --- Clear all auth data ---

export const clearAuthTokens = async (): Promise<void> => {
  await Promise.all([removeToken(), removeRefreshToken()]);
};
