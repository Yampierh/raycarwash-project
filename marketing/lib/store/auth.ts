"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { extractRole, isTokenExpired } from "@/lib/auth";

export type NextStep =
  | "complete_profile"
  | "detailer_onboarding"
  | "ready"
  | null;

export type AuthUser = {
  id?: string;
  email?: string;
  full_name?: string;
  service_type?: "detailer" | null;
  verification_status?: "not_submitted" | "pending" | "approved" | "rejected";
};

export type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  onboardingToken: string | null;
  role: string | null;
  user: AuthUser | null;
  nextStep: NextStep;
  hydrated: boolean;

  setSession: (tokens: {
    access_token?: string | null;
    refresh_token?: string | null;
    onboarding_token?: string | null;
    next_step?: NextStep;
    user?: AuthUser | null;
  }) => void;
  setUser: (user: AuthUser | null) => void;
  clear: () => void;
  isAuthenticated: () => boolean;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      onboardingToken: null,
      role: null,
      user: null,
      nextStep: null,
      hydrated: false,

      setSession: (tokens) =>
        set((state) => {
          const access = tokens.access_token ?? state.accessToken;
          return {
            accessToken: tokens.access_token ?? state.accessToken,
            refreshToken: tokens.refresh_token ?? state.refreshToken,
            onboardingToken:
              tokens.onboarding_token !== undefined
                ? tokens.onboarding_token
                : state.onboardingToken,
            role: access ? extractRole(access) : state.role,
            user: tokens.user !== undefined ? tokens.user : state.user,
            nextStep:
              tokens.next_step !== undefined ? tokens.next_step : state.nextStep,
          };
        }),

      setUser: (user) => set({ user }),

      clear: () =>
        set({
          accessToken: null,
          refreshToken: null,
          onboardingToken: null,
          role: null,
          user: null,
          nextStep: null,
        }),

      isAuthenticated: () => {
        const token = get().accessToken;
        return !!token && !isTokenExpired(token);
      },
    }),
    {
      name: "raycarwash-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({
        accessToken: s.accessToken,
        refreshToken: s.refreshToken,
        onboardingToken: s.onboardingToken,
        user: s.user,
        nextStep: s.nextStep,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.hydrated = true;
          if (state.accessToken) {
            if (isTokenExpired(state.accessToken)) {
              state.accessToken = null;
              state.role = null;
            } else {
              state.role = extractRole(state.accessToken);
            }
          }
        }
      },
    }
  )
);
