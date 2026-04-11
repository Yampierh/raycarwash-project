/**
 * Zustand auth store — Sprint 6
 *
 * Provides synchronous access to the current JWT and roles so that the
 * WebSocket hook can read the token without an async SecureStore call.
 *
 * Hydration: call setTokens() once at app boot after reading from SecureStore.
 * The axios interceptor continues to read from SecureStore for regular requests;
 * this store exists specifically to enable synchronous token access in WS connections.
 */

import { create } from "zustand";

interface AuthState {
  /** Raw JWT access token (null = not authenticated) */
  token: string | null;
  /** User's role names, e.g. ["detailer"] or ["client"] */
  roles: string[];

  /** Set both tokens after login or token refresh */
  setTokens: (token: string, roles: string[]) => void;
  /** Clear store on logout */
  clear: () => void;

  // Convenience role helpers
  isDetailer: () => boolean;
  isClient: () => boolean;
  isAdmin: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  roles: [],

  setTokens: (token, roles) => set({ token, roles }),

  clear: () => set({ token: null, roles: [] }),

  isDetailer: () => get().roles.includes("detailer"),
  isClient: () => get().roles.includes("client"),
  isAdmin: () => get().roles.includes("admin"),
}));
