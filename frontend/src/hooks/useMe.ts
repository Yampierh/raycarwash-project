/**
 * frontend/src/hooks/useMe.ts
 *
 * React Query wrapper for the Profile Hub. One hook per pattern:
 *
 *   useMe(["profile","stats"])              — read Hub for the current screen
 *   useUpdateProfile()                      — PATCH /users/me + optimistic
 *
 * `queryKey` is `["users", "me", sortedTokens.join(",")]` so different
 * include sets cache independently. Components that need multiple sets
 * (e.g. UserHubScreen wants profile+stats, then SecurityScreen wants
 * security+sessions) just call `useMe` again with the new tokens — React
 * Query dedupes the in-flight request and shares the response across
 * subscribers.
 *
 * StepUpRequiredError surfaces as a thrown error (the interceptor in
 * services/api.ts turns the 401 response into that class). Components can
 * `if (error instanceof StepUpRequiredError) showStepUpModal()` from the
 * `error` field.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";

import { ApiError, StepUpRequiredError } from "../lib/api-error";
import {
  getHub,
  updateProfile,
  type HubInclude,
  type HubResult,
  type UpdateProfileBody,
} from "../services/users.service";

// ─── Query key helpers ───────────────────────────────────────────────────────

function hubKey(includes: HubInclude[]): readonly unknown[] {
  return ["users", "me", [...includes].sort().join(",")] as const;
}

// ─── Read hook ───────────────────────────────────────────────────────────────

export interface UseMeOptions {
  /** When true the server returns 200 even if step-up is missing, with
   * sensitive blocks omitted. Use for background refresh that mustn't
   * interrupt the UI. */
  skipStepUp?: boolean;
  /** Pass-through of React Query options (enabled, retry, etc.). */
  query?: Omit<
    UseQueryOptions<HubResult, ApiError | StepUpRequiredError>,
    "queryKey" | "queryFn"
  >;
}

export function useMe(includes: HubInclude[] = [], options: UseMeOptions = {}) {
  return useQuery<HubResult, ApiError | StepUpRequiredError>({
    queryKey: hubKey(includes),
    queryFn: () => getHub(includes, { skipStepUp: options.skipStepUp }),
    ...options.query,
  });
}

// ─── Mutation hook ───────────────────────────────────────────────────────────

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation<HubResult, ApiError | StepUpRequiredError, UpdateProfileBody>({
    mutationFn: updateProfile,
    onSuccess: (result) => {
      // The server returns profile+stats. Update every cached Hub variant
      // that includes those tokens so SecurityScreen / VehiclesScreen don't
      // refetch unnecessarily.
      queryClient.setQueriesData<HubResult>(
        { queryKey: ["users", "me"] },
        (prev) => {
          if (!prev) return prev;
          return {
            data: { ...prev.data, ...result.data },
            meta: { ...prev.meta, ...result.meta },
          };
        },
      );
    },
  });
}

// ─── Prefetch helper for navigation-on-intent (ADR-002b §7.3) ────────────────

/**
 * Trigger a Hub fetch in the background. Call from `onPress` or a
 * navigation `focus` listener so the target screen mounts with warm data.
 *
 *   await prefetchMe(queryClient, ["security", "sessions"]);
 *   navigation.navigate("SecurityScreen");
 */
export async function prefetchMe(
  queryClient: ReturnType<typeof useQueryClient>,
  includes: HubInclude[],
  options: UseMeOptions = {},
): Promise<void> {
  await queryClient.prefetchQuery({
    queryKey: hubKey(includes),
    queryFn: () => getHub(includes, { skipStepUp: options.skipStepUp }),
  });
}
