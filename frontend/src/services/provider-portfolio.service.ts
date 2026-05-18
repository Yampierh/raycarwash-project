/**
 * frontend/src/services/provider-portfolio.service.ts
 *
 * Wraps /api/v1/users/me/provider-portfolio (Phase 5 chunk Y3).
 * Two-step upload mirrors vehicle-photos.service.
 */
import { apiClient, unwrap } from "./api";
import { uploadToPresigned } from "./s3-uploader";

export interface PortfolioPhoto {
  id: string;
  provider_user_id: string;
  s3_key: string;
  caption: string | null;
  tag: string | null;
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

export async function listPortfolio(): Promise<PortfolioPhoto[]> {
  const res = await apiClient.get("/api/v1/users/me/provider-portfolio");
  return unwrap<PortfolioPhoto[]>(res);
}

export async function uploadPortfolioPhoto(
  blob: Blob,
  mimeType: string,
  sizeBytes: number,
  caption?: string,
  tag?: string,
): Promise<PortfolioPhoto> {
  const urlRes = await apiClient.post(
    "/api/v1/users/me/provider-portfolio/upload-url",
    { mime_type: mimeType, size_bytes: sizeBytes },
  );
  const presigned = unwrap<UploadUrlResponse>(urlRes);

  await uploadToPresigned(presigned, blob, mimeType);

  const confirmRes = await apiClient.post(
    "/api/v1/users/me/provider-portfolio",
    {
      s3_key: presigned.s3_key,
      caption: caption ?? null,
      tag: tag ?? null,
    },
  );
  return unwrap<PortfolioPhoto>(confirmRes);
}

export async function deletePortfolioPhoto(photoId: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/me/provider-portfolio/${photoId}`);
}
