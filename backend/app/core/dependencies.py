"""
app/core/dependencies.py — FastAPI dependency factories that bind external
adapters according to the active environment.

Adapters returned here implement the protocols in `infrastructure/storage/`,
`infrastructure/email/`, etc. Routers and services depend on the protocol —
never on a concrete adapter — so production deployments swap implementations
by flipping `RAYCARWASH_ENV` without changing handler code.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from infrastructure.storage.base import FileStorageAdapter
from infrastructure.storage.local import LocalStorageAdapter


# Logical bucket names. Two buckets per ADR-008: public CDN-served and
# private SSE-KMS-served. In LocalStorageAdapter they become subdirectories
# of STORAGE_LOCAL_PATH.
BUCKET_PUBLIC = "public-assets"
BUCKET_PRIVATE = "private-docs"


@lru_cache(maxsize=4)
def _build_adapter(bucket: str) -> FileStorageAdapter:
    """Cache one adapter instance per bucket — they're stateless."""
    env = get_settings().RAYCARWASH_ENV
    if env == "production":
        # TODO(prod): from infrastructure.storage.s3 import S3StorageAdapter
        # return S3StorageAdapter(bucket=bucket)
        raise RuntimeError(
            "S3StorageAdapter is not implemented yet. "
            "Either implement infrastructure/storage/s3.py or set RAYCARWASH_ENV=development."
        )
    return LocalStorageAdapter(bucket=bucket)


def get_public_storage() -> FileStorageAdapter:
    """Avatars, covers, vehicle photos, provider portfolio."""
    return _build_adapter(BUCKET_PUBLIC)


def get_private_storage() -> FileStorageAdapter:
    """KYC docs, insurance, exports — encrypted at rest in production."""
    return _build_adapter(BUCKET_PRIVATE)
