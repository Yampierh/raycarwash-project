"""
File storage adapters.

Two implementations live behind a common Protocol so handlers and services
remain unchanged when we flip from local-disk (dev) to AWS S3 (prod):

  - `LocalStorageAdapter`  — disk-backed, served via the /dev/upload helper.
  - `S3StorageAdapter`     — TODO(prod): boto3 + presigned PUT + SSE-KMS.

Selection happens in app/core/dependencies.py via `RAYCARWASH_ENV`.
"""

from infrastructure.storage.base import FileStorageAdapter, ObjectNotFound  # noqa: F401
from infrastructure.storage.local import LocalStorageAdapter  # noqa: F401
