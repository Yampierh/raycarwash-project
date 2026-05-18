/**
 * frontend/src/hooks/useProfileResources.ts
 *
 * React Query bindings for the Phase 4 sub-resources under
 * /api/v1/users/me. One file because the hooks all share the same
 * `["users", "me", <resource>]` cache key prefix and the same
 * invalidate-on-mutate strategy — keeping them together avoids the
 * ceremony of five tiny hook files.
 *
 * Mutations invalidate the Profile Hub query alongside their own list
 * key, because chunks T/U/V wired the matching Hub blocks. Any
 * `useMe(["addresses"])` or `useMe(["payment_methods"])` consumer
 * elsewhere in the app will refetch automatically when these mutate.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";

import { ApiError, StepUpRequiredError } from "../lib/api-error";
import {
  createAddress,
  deleteAddress,
  getAddress,
  listAddresses,
  setDefaultAddress,
  updateAddress,
  type Address,
  type AddressCreatePayload,
  type AddressUpdatePayload,
} from "../services/addresses.service";
import {
  getClientPreferences,
  putClientPreferences,
  type ClientPreferences,
} from "../services/client-preferences.service";
import {
  addFavorite,
  listFavorites,
  removeFavorite,
  type FavoriteProvider,
} from "../services/favorites.service";
import {
  createSetupIntent,
  deletePaymentMethod,
  listPaymentMethods,
  setDefaultPaymentMethod,
  type PaymentMethod,
  type SetupIntentResponse,
} from "../services/payment-methods.service";
import {
  deleteVehiclePhoto,
  listVehiclePhotos,
  uploadVehiclePhoto,
  type VehiclePhoto,
} from "../services/vehicle-photos.service";

// ─── cache keys ───────────────────────────────────────────────────────────────

const ADDRESSES_KEY = ["users", "me", "addresses"] as const;
const PAYMENT_METHODS_KEY = ["users", "me", "payment-methods"] as const;
const FAVORITES_KEY = ["users", "me", "favorites"] as const;
const CLIENT_PREFS_KEY = ["users", "me", "client-preferences"] as const;
const VEHICLE_PHOTOS_KEY = (vehicleId: string) =>
  ["users", "me", "vehicles", vehicleId, "photos"] as const;

// Hub queries that mutations should invalidate. The Phase 1 `useMe`
// hook keys on `["users", "me", <sortedIncludes>]`; invalidating the
// whole `["users", "me"]` prefix forces a refetch of any Hub variant
// the user happens to have cached.
const HUB_PREFIX = ["users", "me"] as const;

// ─── Addresses ───────────────────────────────────────────────────────────────

export function useAddresses(
  options?: Omit<UseQueryOptions<Address[], ApiError>, "queryKey" | "queryFn">,
) {
  return useQuery<Address[], ApiError>({
    queryKey: ADDRESSES_KEY,
    queryFn: listAddresses,
    staleTime: 60_000,
    ...options,
  });
}

export function useAddress(id: string | undefined) {
  return useQuery<Address, ApiError>({
    queryKey: [...ADDRESSES_KEY, id],
    queryFn: () => getAddress(id!),
    enabled: Boolean(id),
    staleTime: 60_000,
  });
}

export function useCreateAddress() {
  const qc = useQueryClient();
  return useMutation<Address, ApiError, AddressCreatePayload>({
    mutationFn: createAddress,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADDRESSES_KEY });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useUpdateAddress(id: string) {
  const qc = useQueryClient();
  return useMutation<Address, ApiError, AddressUpdatePayload>({
    mutationFn: (body) => updateAddress(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADDRESSES_KEY });
      qc.invalidateQueries({ queryKey: [...ADDRESSES_KEY, id] });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useSetDefaultAddress() {
  const qc = useQueryClient();
  return useMutation<Address, ApiError, string>({
    mutationFn: setDefaultAddress,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADDRESSES_KEY });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useDeleteAddress() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: deleteAddress,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADDRESSES_KEY });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

// ─── Payment methods ─────────────────────────────────────────────────────────

export function usePaymentMethods(
  options?: Omit<
    UseQueryOptions<PaymentMethod[], ApiError | StepUpRequiredError>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery<PaymentMethod[], ApiError | StepUpRequiredError>({
    queryKey: PAYMENT_METHODS_KEY,
    queryFn: listPaymentMethods,
    staleTime: 60_000,
    ...options,
  });
}

export function useCreateSetupIntent() {
  // No invalidation — the SetupIntent isn't a local row; the matching
  // payment_method.attached webhook will fire and the client should
  // refetch usePaymentMethods on screen focus.
  return useMutation<SetupIntentResponse, ApiError | StepUpRequiredError, string>({
    mutationFn: createSetupIntent,
  });
}

export function useSetDefaultPaymentMethod() {
  const qc = useQueryClient();
  return useMutation<PaymentMethod, ApiError, string>({
    mutationFn: setDefaultPaymentMethod,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PAYMENT_METHODS_KEY });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useDeletePaymentMethod() {
  const qc = useQueryClient();
  return useMutation<void, ApiError | StepUpRequiredError, string>({
    mutationFn: deletePaymentMethod,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PAYMENT_METHODS_KEY });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

// ─── Favorites ───────────────────────────────────────────────────────────────

export function useFavorites(
  options?: Omit<UseQueryOptions<FavoriteProvider[], ApiError>, "queryKey" | "queryFn">,
) {
  return useQuery<FavoriteProvider[], ApiError>({
    queryKey: FAVORITES_KEY,
    queryFn: listFavorites,
    staleTime: 60_000,
    ...options,
  });
}

export function useAddFavorite() {
  const qc = useQueryClient();
  return useMutation<FavoriteProvider, ApiError, string>({
    mutationFn: addFavorite,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: FAVORITES_KEY });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useRemoveFavorite() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: removeFavorite,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: FAVORITES_KEY });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

// ─── Client preferences ──────────────────────────────────────────────────────

export function useClientPreferences() {
  return useQuery<ClientPreferences, ApiError>({
    queryKey: CLIENT_PREFS_KEY,
    queryFn: getClientPreferences,
    staleTime: 60_000,
  });
}

export function usePutClientPreferences() {
  const qc = useQueryClient();
  return useMutation<ClientPreferences, ApiError, ClientPreferences>({
    mutationFn: putClientPreferences,
    onSuccess: (data) => {
      qc.setQueryData(CLIENT_PREFS_KEY, data);
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

// ─── Vehicle photos ──────────────────────────────────────────────────────────

export function useVehiclePhotos(vehicleId: string | undefined) {
  return useQuery<VehiclePhoto[], ApiError>({
    queryKey: vehicleId ? VEHICLE_PHOTOS_KEY(vehicleId) : ["users", "me", "vehicles", "noop", "photos"],
    queryFn: () => listVehiclePhotos(vehicleId!),
    enabled: Boolean(vehicleId),
    staleTime: 60_000,
  });
}

interface UploadPhotoArgs {
  blob: Blob;
  mimeType: string;
  sizeBytes: number;
  caption?: string;
}

export function useUploadVehiclePhoto(vehicleId: string) {
  const qc = useQueryClient();
  return useMutation<VehiclePhoto, ApiError, UploadPhotoArgs>({
    mutationFn: ({ blob, mimeType, sizeBytes, caption }) =>
      uploadVehiclePhoto(vehicleId, blob, mimeType, sizeBytes, caption),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: VEHICLE_PHOTOS_KEY(vehicleId) });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}

export function useDeleteVehiclePhoto(vehicleId: string) {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (photoId) => deleteVehiclePhoto(vehicleId, photoId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: VEHICLE_PHOTOS_KEY(vehicleId) });
      qc.invalidateQueries({ queryKey: HUB_PREFIX });
    },
  });
}
