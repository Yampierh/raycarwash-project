/**
 * frontend/src/lib/react-query.ts
 *
 * Single QueryClient shared across the mobile app. Mounted by
 * `<QueryClientProvider>` at the root of App.tsx.
 *
 * Defaults match the cadence the Profile Hub expects:
 *   staleTime  5 min  — matches the Redis cache TTL for /users/me
 *   gcTime    30 min  — keep the cache around if the user backgrounds the app
 *   retry      1      — RN networks flake; one retry is forgiving but bounded
 *
 * Per-query overrides (longer stale for `vehicles`, no retry for mutations,
 * etc.) live in their respective hooks.
 */
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false, // ignored on RN, kept for clarity
    },
    mutations: {
      retry: 0,
    },
  },
});
