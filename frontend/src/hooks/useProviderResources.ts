/**
 * frontend/src/hooks/useProviderResources.ts
 *
 * React Query bindings for the Phase 5 provider sub-resources under
 * /api/v1/users/me/provider-*. One file because the surface area is
 * cohesive and the cache-invalidation strategy is uniform: mutations
 * invalidate both their own resource list AND the Profile Hub prefix,
 * so any Hub include variant that surfaces provider data refreshes.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";

import { ApiError, StepUpRequiredError } from "../lib/api-error";
import {
  deleteDocument,
  listDocuments,
  uploadDocument,
  type DocumentType,
  type ProviderDocument,
} from "../services/provider-documents.service";
import {
  deletePortfolioPhoto,
  listPortfolio,
  uploadPortfolioPhoto,
  type PortfolioPhoto,
} from "../services/provider-portfolio.service";
import {
  activateProvider,
  deactivateProvider,
  getProviderProfile,
  setProviderStatus,
  updateProvider,
  type ProviderActivatePayload,
  type ProviderProfile,
  type ProviderUpdatePayload,
} from "../services/provider-profile.service";
import {
  getVerificationStatus,
  listAchievements,
  startVerification,
  type Achievement,
  type VerificationStart,
  type VerificationStatus,
} from "../services/provider-verification.service";

// ─── cache keys ───────────────────────────────────────────────────────────────

const PROVIDER_PROFILE_KEY = ["users", "me", "provider-profile"] as const;
const PORTFOLIO_KEY = ["users", "me", "provider-portfolio"] as const;
const DOCUMENTS_KEY = ["users", "me", "provider-documents"] as const;
const VERIFICATION_KEY = ["users", "me", "provider-verification"] as const;
const ACHIEVEMENTS_KEY = ["users", "me", "provider-achievements"] as const;
const HUB_PREFIX = ["users", "me"] as const;

// ─── Provider profile ────────────────────────────────────────────────────────

export function useProviderProfile(
  options?: Omit<UseQueryOptions<ProviderProfile, ApiError>, "queryKey" | "queryFn">,
) {
  return useQuery<ProviderProfile, ApiError>({
    queryKey: PROVIDER_PROFILE_KEY,
    queryFn: getProviderProfile,
    staleTime: 60_000,
    // Don't auto-retry the 404 "not activated yet" — the UI uses it
    // as a signal to show the activation CTA.
    retry: false,
    ...options,
  });
}

export function useActivateProvider() {
  const qc = useQueryClient();
  return useMutation<ProviderProfile, ApiError | StepUpRequiredError, ProviderActivatePayload>({
    mutationFn: activateProvider,
    onSuccess: (data) => {
      qc.setQueryData(PROVIDER_PROFILE_KEY, data);
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useUpdateProvider() {
  const qc = useQueryClient();
  return useMutation<ProviderProfile, ApiError, ProviderUpdatePayload>({
    mutationFn: updateProvider,
    onSuccess: (data) => {
      qc.setQueryData(PROVIDER_PROFILE_KEY, data);
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useDeactivateProvider() {
  const qc = useQueryClient();
  return useMutation<ProviderProfile, ApiError | StepUpRequiredError, void>({
    mutationFn: () => deactivateProvider(),
    onSuccess: (data) => {
      qc.setQueryData(PROVIDER_PROFILE_KEY, data);
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useSetProviderStatus() {
  const qc = useQueryClient();
  return useMutation<ProviderProfile, ApiError, boolean>({
    mutationFn: setProviderStatus,
    onSuccess: (data) => {
      qc.setQueryData(PROVIDER_PROFILE_KEY, data);
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

// ─── Portfolio ───────────────────────────────────────────────────────────────

export function usePortfolio() {
  return useQuery<PortfolioPhoto[], ApiError>({
    queryKey: PORTFOLIO_KEY,
    queryFn: listPortfolio,
    staleTime: 60_000,
    retry: false,
  });
}

interface UploadPortfolioArgs {
  blob: Blob;
  mimeType: string;
  sizeBytes: number;
  caption?: string;
  tag?: string;
}

export function useUploadPortfolioPhoto() {
  const qc = useQueryClient();
  return useMutation<PortfolioPhoto, ApiError, UploadPortfolioArgs>({
    mutationFn: ({ blob, mimeType, sizeBytes, caption, tag }) =>
      uploadPortfolioPhoto(blob, mimeType, sizeBytes, caption, tag),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PORTFOLIO_KEY });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useDeletePortfolioPhoto() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: deletePortfolioPhoto,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PORTFOLIO_KEY });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

// ─── Documents (KYC) ─────────────────────────────────────────────────────────

export function useDocuments() {
  return useQuery<ProviderDocument[], ApiError>({
    queryKey: DOCUMENTS_KEY,
    queryFn: listDocuments,
    // Download URLs are 1 h signed — don't cache for hours.
    staleTime: 30 * 60_000,
    retry: false,
  });
}

interface UploadDocumentArgs {
  blob: Blob;
  type: DocumentType;
  mimeType: string;
  sizeBytes: number;
  title?: string;
  expiresAt?: string;
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation<ProviderDocument, ApiError, UploadDocumentArgs>({
    mutationFn: ({ blob, type, mimeType, sizeBytes, title, expiresAt }) =>
      uploadDocument(blob, type, mimeType, sizeBytes, title, expiresAt),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation<void, ApiError | StepUpRequiredError, string>({
    mutationFn: deleteDocument,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
}

// ─── Verification + Achievements ─────────────────────────────────────────────

export function useVerificationStatus() {
  return useQuery<VerificationStatus, ApiError>({
    queryKey: VERIFICATION_KEY,
    queryFn: getVerificationStatus,
    staleTime: 30_000,
    retry: false,
  });
}

export function useStartVerification() {
  const qc = useQueryClient();
  return useMutation<VerificationStart, ApiError, void>({
    mutationFn: () => startVerification(),
    onSuccess: () => {
      // The start endpoint persists session_id + bumps status to
      // "pending" — invalidate the status query so the UI re-renders
      // the "Resume verification" CTA.
      qc.invalidateQueries({ queryKey: VERIFICATION_KEY });
      qc.invalidateQueries({ queryKey: PROVIDER_PROFILE_KEY });
    },
  });
}

export function useAchievements() {
  return useQuery<Achievement[], ApiError>({
    queryKey: ACHIEVEMENTS_KEY,
    queryFn: listAchievements,
    staleTime: 5 * 60_000,
  });
}
