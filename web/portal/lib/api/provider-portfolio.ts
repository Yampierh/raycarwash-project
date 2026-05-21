import { apiClient, unwrap } from "./client";

export type PortfolioPhoto = {
  id: string;
  provider_user_id: string;
  s3_key: string;
  caption: string | null;
  tag: string | null;
  sort_order: number;
  photo_url: string | null;
  created_at: string;
};

export type PortfolioUploadUrlResponse = {
  url: string;
  method: string;
  headers: Record<string, string>;
  s3_key: string;
  expires_in: number;
};

export async function listPortfolioPhotos(): Promise<PortfolioPhoto[]> {
  const res = await apiClient.get("/users/me/provider-portfolio");
  return unwrap<PortfolioPhoto[]>(res);
}

export async function getPortfolioUploadUrl(body: {
  mime_type: string;
  size_bytes: number;
}): Promise<PortfolioUploadUrlResponse> {
  const res = await apiClient.post("/users/me/provider-portfolio/upload-url", body);
  return unwrap<PortfolioUploadUrlResponse>(res);
}

export async function confirmPortfolioUpload(body: {
  s3_key: string;
  caption?: string;
  tag?: string;
}): Promise<PortfolioPhoto> {
  const res = await apiClient.post("/users/me/provider-portfolio", body);
  return unwrap<PortfolioPhoto>(res);
}

export async function deletePortfolioPhoto(photoId: string): Promise<void> {
  await apiClient.delete(`/users/me/provider-portfolio/${photoId}`);
}

export async function uploadPortfolioPhoto(
  file: File,
  caption?: string,
  tag?: string
): Promise<PortfolioPhoto> {
  const { url, headers, s3_key } = await getPortfolioUploadUrl({
    mime_type: file.type,
    size_bytes: file.size,
  });

  await fetch(url, {
    method: "PUT",
    headers,
    body: file,
  });

  return confirmPortfolioUpload({ s3_key, caption, tag });
}
