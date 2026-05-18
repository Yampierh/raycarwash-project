/**
 * frontend/src/services/vehicle-photos.service.ts
 *
 * Wraps /api/v1/users/me/vehicles/{id}/photos (Phase 4 chunk V).
 *
 * Two-step upload mirrors avatar.service: prepare URL → PUT bytes via
 * s3-uploader → POST confirm. Re-uses uploadBlobToPresigned() so the
 * LocalStorageAdapter vs S3 transport difference stays in one place.
 */
import { apiClient, unwrap } from "./api";
import { uploadToPresigned } from "./s3-uploader";

export interface VehiclePhoto {
  id: string;
  vehicle_id: string;
  s3_key: string;
  caption: string | null;
  sort_order: number;
  photo_url: string | null;
  created_at: string;
}

interface UploadUrlResponse {
  url: string;
  method: string;
  headers: Record<string, string>;
  s3_key: string;
  expires_in: number;
}

export async function listVehiclePhotos(vehicleId: string): Promise<VehiclePhoto[]> {
  const res = await apiClient.get(`/api/v1/users/me/vehicles/${vehicleId}/photos`);
  return unwrap<VehiclePhoto[]>(res);
}

export async function uploadVehiclePhoto(
  vehicleId: string,
  blob: Blob,
  mimeType: string,
  sizeBytes: number,
  caption?: string,
): Promise<VehiclePhoto> {
  // Step 1: request presigned URL.
  const urlRes = await apiClient.post(
    `/api/v1/users/me/vehicles/${vehicleId}/photos/upload-url`,
    { mime_type: mimeType, size_bytes: sizeBytes },
  );
  const presigned = unwrap<UploadUrlResponse>(urlRes);

  // Step 2: PUT the bytes via the shared uploader (handles dev /dev/upload
  // and prod S3 with the right verb + headers).
  await uploadToPresigned(presigned, blob, mimeType);

  // Step 3: confirm.
  const confirmRes = await apiClient.post(
    `/api/v1/users/me/vehicles/${vehicleId}/photos`,
    { s3_key: presigned.s3_key, caption: caption ?? null },
  );
  return unwrap<VehiclePhoto>(confirmRes);
}

export async function deleteVehiclePhoto(
  vehicleId: string,
  photoId: string,
): Promise<void> {
  await apiClient.delete(
    `/api/v1/users/me/vehicles/${vehicleId}/photos/${photoId}`,
  );
}
