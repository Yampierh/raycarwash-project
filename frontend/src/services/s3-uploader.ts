/**
 * frontend/src/services/s3-uploader.ts
 *
 * One-shot binary uploader for presigned URLs returned by
 * /api/v1/users/me/avatar/upload-url (and any future
 * /<resource>/upload-url endpoint). Works against both:
 *
 *   - S3 presigned URLs (PUT, absolute https://). Native fetch handles it.
 *   - LocalStorageAdapter dev URLs (POST, relative /dev/upload?...). We
 *     prepend the API base URL so the fetch hits the FastAPI server.
 *
 * The image bytes come from expo-image-picker (uri → fetch+blob).
 * expo-image-manipulator can optionally resize before upload — pass it
 * through `prepareImageBytes` in the AvatarPicker.
 */
import { APP_CONFIG } from "../config/app.config";

const SERVER_URL = process.env.EXPO_PUBLIC_API_URL || APP_CONFIG.apiBaseUrl;

export interface PresignedUpload {
  url: string;
  method: string;
  headers: Record<string, string>;
  s3_key: string;
  expires_in: number;
}

/**
 * Read a `file://` URI from the device and return the raw bytes as a Blob.
 * React Native's fetch can read these URIs directly; on web the same trick
 * works for blob: URLs.
 */
export async function uriToBlob(uri: string): Promise<Blob> {
  const response = await fetch(uri);
  if (!response.ok) {
    throw new Error(`Could not read local image (${response.status})`);
  }
  return await response.blob();
}

/**
 * Upload the bytes returned by uriToBlob to the URL handed back by
 * /upload-url. Resolves on 2xx, throws otherwise. Returns the s3_key the
 * caller should pass to the confirm endpoint.
 */
export async function uploadToPresigned(
  presigned: PresignedUpload,
  blob: Blob,
  mimeType: string,
): Promise<string> {
  // LocalStorageAdapter returns a relative path — prefix the backend URL.
  const fullUrl = presigned.url.startsWith("http")
    ? presigned.url
    : `${SERVER_URL}${presigned.url}`;

  const response = await fetch(fullUrl, {
    method: presigned.method,
    headers: {
      ...presigned.headers,
      "Content-Type": mimeType,
    },
    body: blob,
  });

  if (!response.ok) {
    let detail = `Upload failed (${response.status})`;
    try {
      const body = await response.text();
      detail = `${detail}: ${body.slice(0, 200)}`;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  return presigned.s3_key;
}
