/**
 * marketing/lib/hooks/useMeHub.ts
 *
 * SWR hook for the Profile Hub. Distinct from the legacy `useMe()` (which
 * still talks to /auth/me). Each page migrates to `useMeHub` on its own
 * cadence; the two hooks coexist during the transition window.
 *
 * The SWR key encodes the sorted include tokens so different screens'
 * `?include=` sets cache independently.
 */
"use client";

import useSWR, { useSWRConfig } from "swr";
import { getHub, type HubInclude, type HubResult } from "@/lib/api/users-hub";

function hubKey(includes: HubInclude[]): string {
  return `hub:${[...includes].sort().join(",")}`;
}

export interface UseMeHubOptions {
  /** Set true to receive 200 with sensitive blocks omitted when step-up
   * is missing (instead of throwing the StepUpRequiredError). */
  skipStepUp?: boolean;
}

export function useMeHub(includes: HubInclude[] = [], options: UseMeHubOptions = {}) {
  return useSWR<HubResult>(
    hubKey(includes),
    () => getHub(includes, { skipStepUp: options.skipStepUp }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 5 * 60_000, // matches Redis cache TTL
    },
  );
}

/**
 * Invalidate every cached Hub variant. Call after a mutation so subsequent
 * `useMeHub` reads pick up the new data even if the SWR key differs.
 */
export function useInvalidateMeHub() {
  const { mutate } = useSWRConfig();
  return () => mutate((key) => typeof key === "string" && key.startsWith("hub:"), undefined, {
    revalidate: true,
  });
}
