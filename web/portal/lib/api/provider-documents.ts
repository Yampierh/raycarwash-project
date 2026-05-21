import { apiClient, unwrap } from "./client";

export const DOCUMENT_TYPES = [
  "insurance",
  "business_license",
  "certification",
  "w9",
  "other",
] as const;

export type DocumentType = (typeof DOCUMENT_TYPES)[number];

export type ProviderDocument = {
  id: string;
  user_id: string;
  type: string;
  title: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  expires_at: string | null;
  download_url: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentUploadUrlResponse = {
  url: string;
  method: string;
  headers: Record<string, string>;
  s3_key: string;
  expires_in: number;
};

export async function listProviderDocuments(): Promise<ProviderDocument[]> {
  const res = await apiClient.get("/users/me/provider-documents");
  return unwrap<ProviderDocument[]>(res);
}

export async function getDocumentUploadUrl(body: {
  type: string;
  mime_type: string;
  size_bytes: number;
}): Promise<DocumentUploadUrlResponse> {
  const res = await apiClient.post("/users/me/provider-documents/upload-url", body);
  return unwrap<DocumentUploadUrlResponse>(res);
}

export async function confirmDocumentUpload(body: {
  s3_key: string;
  title?: string;
  type: string;
  expires_at?: string;
}): Promise<ProviderDocument> {
  const res = await apiClient.post("/users/me/provider-documents", body);
  return unwrap<ProviderDocument>(res);
}

export async function deleteProviderDocument(docId: string): Promise<void> {
  await apiClient.delete(`/users/me/provider-documents/${docId}`);
}

export async function uploadProviderDocument(
  file: File,
  type: string,
  title?: string,
  expires_at?: string
): Promise<ProviderDocument> {
  const { url, headers, s3_key } = await getDocumentUploadUrl({
    type,
    mime_type: file.type,
    size_bytes: file.size,
  });

  await fetch(url, {
    method: "PUT",
    headers,
    body: file,
  });

  return confirmDocumentUpload({ s3_key, type, title, expires_at });
}
