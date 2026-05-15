"""
infrastructure/storage/base.py — FileStorageAdapter protocol (ADR-008).

All storage operations go through this interface so swapping LocalStorageAdapter
for S3StorageAdapter requires no changes in routers or services. Returned
shapes are stable across implementations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ObjectNotFound(Exception):
    """Raised when head/delete is attempted on a non-existent key."""


@dataclass(frozen=True)
class PresignedUpload:
    """
    Shape returned by `generate_upload_url`. The frontend issues a single
    HTTP request (`method` + `headers`) to `url`, body = file bytes.

    For S3 this is a true presigned URL; for LocalStorageAdapter it's a
    relative path with an HMAC signature query param consumed by
    /dev/upload.
    """
    url: str
    method: str
    headers: dict[str, str]
    s3_key: str
    expires_in: int  # seconds


@dataclass(frozen=True)
class ObjectMeta:
    """Subset of S3 HeadObject output used by avatar/document services."""
    size: int
    content_type: str | None


class FileStorageAdapter(Protocol):
    """Concrete adapters implement these four operations."""

    bucket: str  # logical bucket name ("public-assets" | "private-docs")

    async def generate_upload_url(
        self,
        key: str,
        *,
        mime: str,
        max_size: int,
        ttl_seconds: int = 3600,
    ) -> PresignedUpload: ...

    async def head_object(self, key: str) -> ObjectMeta:
        """Raises ObjectNotFound if the key doesn't exist."""

    async def generate_download_url(
        self,
        key: str,
        *,
        ttl_seconds: int = 86_400,
    ) -> str: ...

    async def delete_object(self, key: str) -> None:
        """No-op if the key doesn't exist (idempotent)."""
