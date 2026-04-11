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

// --- Biometric preference ---

const BIOMETRIC_KEY = "raycarwash_biometric_enabled";

export const setBiometricEnabled = async (enabled: boolean): Promise<void> => {
  if (enabled) {
    await SecureStore.setItemAsync(BIOMETRIC_KEY, "true");
  } else {
    await SecureStore.deleteItemAsync(BIOMETRIC_KEY);
  }
};

export const getBiometricEnabled = async (): Promise<boolean> => {
  const val = await SecureStore.getItemAsync(BIOMETRIC_KEY);
  return val === "true";
};

// --- Last signed-in email (for passkey auto-unlock on app open) ---

const LAST_EMAIL_KEY = "raycarwash_last_email";

export const saveLastEmail = async (email: string): Promise<void> => {
  await SecureStore.setItemAsync(LAST_EMAIL_KEY, email);
};

export const getLastEmail = async (): Promise<string | null> => {
  return await SecureStore.getItemAsync(LAST_EMAIL_KEY);
};

// --- Passkey preference ---

const PASSKEY_KEY = "raycarwash_passkey_enabled";

export const setPasskeyEnabled = async (enabled: boolean): Promise<void> => {
  if (enabled) {
    await SecureStore.setItemAsync(PASSKEY_KEY, "true");
  } else {
    await SecureStore.deleteItemAsync(PASSKEY_KEY);
  }
};

export const getPasskeyEnabled = async (): Promise<boolean> => {
  const val = await SecureStore.getItemAsync(PASSKEY_KEY);
  return val === "true";
};
