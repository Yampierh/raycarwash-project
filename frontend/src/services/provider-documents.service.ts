/**
 * frontend/src/services/provider-documents.service.ts
 *
 * Wraps /api/v1/users/me/provider-documents (Phase 5 chunk Y4).
 *
 * Download URLs in the list payload are 1 h signed — re-fetch the
 * list when the screen mounts rather than caching URLs client-side
 * past their TTL.
 */
import { apiClient, unwrap } from "./api";
import { uploadToPresigned } from "./s3-uploader";

export type DocumentType =
  | "insurance"
  | "business_license"
  | "certification"
  | "w9"
  | "other";

export interface ProviderDocument {
  id: string;
  user_id: string;
  type: DocumentType;
  title: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  expires_at: string | null;
  download_url: string | null;
  created_at: string;
  updated_at: string;
}

interface UploadUrlResponse {
  url: string;
  method: string;
  headers: Record<string, string>;
  s3_key: string;
  expires_in: number;
}

export async function listDocuments(): Promise<ProviderDocument[]> {
  const res = await apiClient.get("/api/v1/users/me/provider-documents");
  return unwrap<ProviderDocument[]>(res);
}

export async function uploadDocument(
  blob: Blob,
  type: DocumentType,
  mimeType: string,
  sizeBytes: number,
  title?: string,
  expiresAt?: string,
): Promise<ProviderDocument> {
  const urlRes = await apiClient.post(
    "/api/v1/users/me/provider-documents/upload-url",
    { type, mime_type: mimeType, size_bytes: sizeBytes },
  );
  const presigned = unwrap<UploadUrlResponse>(urlRes);

  await uploadToPresigned(presigned, blob, mimeType);

  const confirmRes = await apiClient.post(
    "/api/v1/users/me/provider-documents",
    {
      s3_key: presigned.s3_key,
      type,
      title: title ?? null,
      expires_at: expiresAt ?? null,
    },
  );
  return unwrap<ProviderDocument>(confirmRes);
}

export async function deleteDocument(docId: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/me/provider-documents/${docId}`);
}
