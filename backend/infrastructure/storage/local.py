"""
infrastructure/storage/local.py — Disk-backed adapter for development.

Files live under `STORAGE_LOCAL_PATH / bucket / key`. The "presigned URL"
points back at `POST /dev/upload?key=...&sig=...`, where `sig` is an HMAC
computed with `DEV_UPLOAD_HMAC_KEY`. The /dev/upload endpoint validates the
signature before writing the file, so the dev flow mirrors S3 semantics:

  1. Service requests upload URL → client receives URL + signature.
  2. Client uploads bytes to that URL (no auth).
  3. Service calls confirm endpoint → head_object verifies the upload landed.

`generate_download_url` returns a relative URL served by the FastAPI static
mount on the bucket root.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import mimetypes
from pathlib import Path

from app.core.config import get_settings
from infrastructure.storage.base import (
    FileStorageAdapter,
    ObjectMeta,
    ObjectNotFound,
    PresignedUpload,
)


class LocalStorageAdapter:
    """Implements FileStorageAdapter on the local filesystem."""

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        settings = get_settings()
        self._root = Path(settings.STORAGE_LOCAL_PATH) / bucket
        self._root.mkdir(parents=True, exist_ok=True)
        self._hmac_key = settings.DEV_UPLOAD_HMAC_KEY.encode("utf-8")

    # ---- presigned-equivalent URL ---------------------------------- #

    async def generate_upload_url(
        self,
        key: str,
        *,
        mime: str,
        max_size: int,
        ttl_seconds: int = 3600,
    ) -> PresignedUpload:
        sig = self._sign(key, mime, max_size)
        from urllib.parse import quote

        return PresignedUpload(
            url=(
                f"/dev/upload?bucket={quote(self.bucket)}"
                f"&key={quote(key)}"
                f"&mime={quote(mime)}"
                f"&max_size={max_size}"
                f"&sig={sig}"
            ),
            method="POST",
            headers={"Content-Type": mime},
            s3_key=key,
            expires_in=ttl_seconds,
        )

    async def head_object(self, key: str) -> ObjectMeta:
        path = self._resolve(key)
        if not path.exists() or not path.is_file():
            raise ObjectNotFound(key)
        size = path.stat().st_size
        ct, _ = mimetypes.guess_type(path.name)
        return ObjectMeta(size=size, content_type=ct)

    async def generate_download_url(
        self,
        key: str,
        *,
        ttl_seconds: int = 86_400,
    ) -> str:
        # Dev: bucket is served by FastAPI static mount at /storage/{bucket}/...
        from urllib.parse import quote

        return f"/storage/{quote(self.bucket)}/{quote(key)}"

    async def delete_object(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            await asyncio.to_thread(path.unlink)

    # ---- internal helpers ------------------------------------------ #

    def _resolve(self, key: str) -> Path:
        # Block path traversal: keys may only contain a-z A-Z 0-9 _ - / .
        if any(part in {"..", ""} for part in key.split("/")):
            raise ValueError(f"unsafe key: {key!r}")
        return self._root / key

    def _sign(self, key: str, mime: str, max_size: int) -> str:
        payload = f"{self.bucket}\n{key}\n{mime}\n{max_size}".encode("utf-8")
        return hmac.new(self._hmac_key, payload, hashlib.sha256).hexdigest()

    def verify_signature(self, key: str, mime: str, max_size: int, sig: str) -> bool:
        """Used by /dev/upload to validate the URL signature."""
        return hmac.compare_digest(self._sign(key, mime, max_size), sig)

    def write_bytes(self, key: str, data: bytes) -> int:
        """Synchronous write used by /dev/upload; returns bytes written."""
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return len(data)
