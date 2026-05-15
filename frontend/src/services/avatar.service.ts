/**
 * frontend/src/services/avatar.service.ts
 *
 * Wraps the three avatar endpoints (Phase 2 chunk K):
 *   POST   /users/me/avatar/upload-url
 *   POST   /users/me/avatar               (confirm)
 *   DELETE /users/me/avatar
 *
 * Each function returns the unwrapped envelope `data` so callers can
 * `const url = await confirmAvatarUpload(...)`. Errors propagate as the
 * typed ApiError / StepUpRequiredError from Phase 0 chunk F.
 *
 * `uploadAvatar(uri, mimeType, sizeBytes)` is the convenience function
 * AvatarPicker uses — orchestrates upload-url → bytes PUT → confirm in
 * one call.
 */
import { apiClient, unwrap } from "./api";
import {
  uploadToPresigned,
  uriToBlob,
  type PresignedUpload,
} from "./s3-uploader";

// ─── Request types (mirror backend avatar_schemas.py) ─────────────────────────

export interface UploadUrlRequest {
  mime_type: string;
  size_bytes: number;
}

export interface AvatarConfirmResponse {
  avatar_url: string | null;
  cover_url: string | null;
}

// ─── Low-level endpoints ──────────────────────────────────────────────────────

export async function requestAvatarUploadUrl(
  body: UploadUrlRequest,
): Promise<PresignedUpload> {
  const response = await apiClient.post("/users/me/avatar/upload-url", body);
  return unwrap<PresignedUpload>(response);
}

export async function confirmAvatarUpload(s3Key: string): Promise<AvatarConfirmResponse> {
  const response = await apiClient.post("/users/me/avatar", { s3_key: s3Key });
  return unwrap<AvatarConfirmResponse>(response);
}

export async function deleteAvatar(): Promise<void> {
  await apiClient.delete("/users/me/avatar");
}

// ─── Convenience: end-to-end upload ───────────────────────────────────────────

/**
 * Run the full presigned → bytes → confirm flow. Returns the signed URL
 * the backend persisted on the User (relative path in dev, CloudFront in
 * production). Callers should pass it to React Query / SWR cache updates
 * or invalidate `["users","me", "profile"]` so the Hub re-fetches.
 */
export async function uploadAvatar(
  localUri: string,
  mimeType: string,
  sizeBytes: number,
): Promise<string> {
  const presigned = await requestAvatarUploadUrl({
    mime_type: mimeType,
    size_bytes: sizeBytes,
  });
  const blob = await uriToBlob(localUri);
  await uploadToPresigned(presigned, blob, mimeType);
  const result = await confirmAvatarUpload(presigned.s3_key);
  if (!result.avatar_url) {
    throw new Error("Backend confirmed the upload but returned no avatar_url");
  }
  return result.avatar_url;
}
