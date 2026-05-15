/**
 * frontend/src/hooks/useAuthSecurity.ts
 *
 * React Query bindings for the security center (/auth/security,
 * /auth/history) and TOTP mutation hooks. Mirrors the useMe pattern from
 * Phase 1 so SecurityScreen + ChangeXxxScreen can read state without
 * managing their own loading.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";

import { ApiError, StepUpRequiredError } from "../lib/api-error";
import {
  disableTotp,
  enrollTotp,
  getSecurityHistory,
  getSecuritySummary,
  listPasskeys,
  regenerateBackupCodes,
  renamePasskey,
  revokePasskey,
  verifyTotp,
  type PasskeySummary,
  type SecurityHistoryItem,
  type SecuritySummary,
  type TotpEnrollResult,
} from "../services/auth-security.service";

const SUMMARY_KEY = ["auth", "security"] as const;
const HISTORY_KEY = ["auth", "history"] as const;
const PASSKEYS_KEY = ["auth", "passkeys"] as const;

// ─── queries ──────────────────────────────────────────────────────────────────

export function useSecuritySummary(
  options?: Omit<
    UseQueryOptions<SecuritySummary, ApiError | StepUpRequiredError>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery<SecuritySummary, ApiError | StepUpRequiredError>({
    queryKey: SUMMARY_KEY,
    queryFn: getSecuritySummary,
    staleTime: 60_000, // 1 min — security state is sticky
    ...options,
  });
}

export function useSecurityHistory(limit = 20) {
  return useQuery<SecurityHistoryItem[], ApiError | StepUpRequiredError>({
    queryKey: [...HISTORY_KEY, limit],
    queryFn: () => getSecurityHistory(limit),
    staleTime: 30_000,
  });
}

export function usePasskeys() {
  return useQuery<PasskeySummary[], ApiError | StepUpRequiredError>({
    queryKey: PASSKEYS_KEY,
    queryFn: listPasskeys,
    staleTime: 60_000,
  });
}

// ─── mutations ────────────────────────────────────────────────────────────────

export function useEnrollTotp() {
  const queryClient = useQueryClient();
  return useMutation<TotpEnrollResult, ApiError | StepUpRequiredError, void>({
    mutationFn: () => enrollTotp(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUMMARY_KEY });
      queryClient.invalidateQueries({ queryKey: ["users", "me"] });
    },
  });
}

export function useVerifyTotp() {
  const queryClient = useQueryClient();
  return useMutation<SecuritySummary, ApiError | StepUpRequiredError, string>({
    mutationFn: (code) => verifyTotp(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUMMARY_KEY });
      queryClient.invalidateQueries({ queryKey: ["users", "me"] });
    },
  });
}

export function useDisableTotp() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError | StepUpRequiredError, void>({
    mutationFn: () => disableTotp(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SUMMARY_KEY });
      queryClient.invalidateQueries({ queryKey: ["users", "me"] });
    },
  });
}

export function useRegenerateBackupCodes() {
  return useMutation<string[], ApiError | StepUpRequiredError, void>({
    mutationFn: () => regenerateBackupCodes(),
  });
}

export function useRenamePasskey() {
  const queryClient = useQueryClient();
  return useMutation<
    PasskeySummary,
    ApiError | StepUpRequiredError,
    { id: string; deviceName: string }
  >({
    mutationFn: ({ id, deviceName }) => renamePasskey(id, deviceName),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PASSKEYS_KEY }),
  });
}

export function useRevokePasskey() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError | StepUpRequiredError, string>({
    mutationFn: (id) => revokePasskey(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PASSKEYS_KEY });
      queryClient.invalidateQueries({ queryKey: SUMMARY_KEY });
    },
  });
}
