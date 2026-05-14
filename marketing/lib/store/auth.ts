"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { extractRole, isTokenExpired } from "@/lib/auth";

export type NextStep =
  | "complete_profile"
  | "detailer_onboarding"
  | "ready"
  | null;

export type RoleIntent = "client" | "detailer";
export type ActiveRole = "client" | "detailer" | "admin";

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
  roles: string[];
  /** User's last picked entry mode (persists across logout for UX). */
  roleIntent: RoleIntent | null;
  /** The role the user is currently operating as in this session. */
  activeRole: ActiveRole | null;
  user: AuthUser | null;
  nextStep: NextStep;
  hydrated: boolean;

  setSession: (tokens: {
    access_token?: string | null;
    refresh_token?: string | null;
    onboarding_token?: string | null;
    roles?: string[] | null;
    active_role?: ActiveRole | null;
    next_step?: NextStep;
    user?: AuthUser | null;
  }) => void;
  setRoleIntent: (intent: RoleIntent) => void;
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
      roles: [],
      roleIntent: null,
      activeRole: null,
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
            // Preserve existing roles when not provided (e.g. refresh token flow
            // returns no roles list). Empty array is a valid explicit "no roles".
            roles: tokens.roles != null ? tokens.roles : state.roles,
            activeRole:
              tokens.active_role !== undefined
                ? tokens.active_role
                : state.activeRole,
            user: tokens.user !== undefined ? tokens.user : state.user,
            nextStep:
              tokens.next_step !== undefined ? tokens.next_step : state.nextStep,
          };
        }),

      setRoleIntent: (intent) => set({ roleIntent: intent }),

      setUser: (user) => set({ user }),

      clear: () =>
        set((state) => ({
          accessToken: null,
          refreshToken: null,
          onboardingToken: null,
          role: null,
          roles: [],
          activeRole: null,
          user: null,
          nextStep: null,
          // Keep roleIntent across logout — it's a UX preference, not auth state.
          roleIntent: state.roleIntent,
        })),

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
        roles: s.roles,
        roleIntent: s.roleIntent,
        activeRole: s.activeRole,
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
              state.roles = [];
              state.activeRole = null;
            } else {
              state.role = extractRole(state.accessToken);
            }
          }
        }
      },
    }
  )
);
