"""
domains/users/provider_documents_service.py — orchestration for
`/api/v1/users/me/provider-documents*` (Phase 5 chunk Y4).

KYC artifacts (insurance certificates, business licenses, W-9, etc.)
landed in the PRIVATE S3 bucket (ADR-008). Download URLs are 1-hour
presigned per the spec — the listing endpoint signs them at read time
so the frontend can render thumbnails / "view PDF" actions without
the keys ever appearing in plain text.

The model lives in `domains/users/document.py` keyed on `user_id`
(not provider_user_id) so the artifacts survive a provider →
client-only role switch — they remain tied to the account.

Activate-required guard mirrors the portfolio service: every operation
returns 409 with "Activate provider mode" if the caller hasn't yet
called POST /me/provider-profile.

The expires_at field powers the Phase 5 chunk Y6
`document_expiry_checker` worker — no service-layer behaviour here
beyond accepting the value at confirm-time.
"""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_private_storage
from app.middleware.audit_context import AuditContext, get_audit_context
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.providers.models import ProviderProfile
from domains.users.document import Document
from domains.users.models import User
from domains.users.provider_documents_schemas import (
    ALLOWED_DOCUMENT_MIME_TYPES,
    MAX_DOCUMENT_SIZE_BYTES,
    VALID_DOCUMENT_TYPES,
)
from infrastructure.storage.base import (
    FileStorageAdapter,
    ObjectNotFound,
    PresignedUpload,
)

logger = logging.getLogger(__name__)


_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "application/pdf": "pdf",
}

# 1-hour download presigns. Documents may contain SSN, EIN, or
# insurance policy numbers — short TTL is the difference between a
# leaked browser-history URL being useful for minutes vs. days.
_DOWNLOAD_TTL_SECONDS = 3600


class DocumentServiceError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


class ProviderDocumentsService:
    def __init__(self, db: AsyncSession, audit_ctx: AuditContext) -> None:
        self.db = db
        self.audit_ctx = audit_ctx
        self.audit_repo = AuditRepository(db)
        self._adapter: FileStorageAdapter = get_private_storage()

    # ─── Guards ─────────────────────────────────────────────────────────────

    async def _require_provider(self, user: User) -> None:
        pp = (await self.db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user.id)
        )).scalar_one_or_none()
        if pp is None:
            raise DocumentServiceError(
                status.HTTP_409_CONFLICT,
                "conflict",
                "Activate provider mode before managing KYC documents.",
            )

    # ─── List ───────────────────────────────────────────────────────────────

    async def list_for_user(self, user: User) -> list[tuple[Document, str | None]]:
        """Returns each Document paired with a freshly-signed download URL.
        Soft-deleted rows are excluded — the worker doc_expiry_checker
        only scans is_deleted=false rows anyway."""
        await self._require_provider(user)
        rows = (await self.db.scalars(
            select(Document)
            .where(
                Document.user_id == user.id,
                Document.is_deleted.is_(False),
            )
            .order_by(Document.type, Document.created_at.desc())
        )).all()
        out: list[tuple[Document, str | None]] = []
        for row in rows:
            url = await self._sign_download(row.s3_key)
            out.append((row, url))
        return out

    async def get_or_404(
        self, user: User, doc_id: uuid.UUID,
    ) -> tuple[Document, str | None]:
        row = (await self.db.execute(
            select(Document)
            .where(
                Document.id == doc_id,
                Document.user_id == user.id,
                Document.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if row is None:
            raise DocumentServiceError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "Document not found.",
            )
        url = await self._sign_download(row.s3_key)
        return row, url

    # ─── upload-url ─────────────────────────────────────────────────────────

    async def prepare_upload(
        self, user: User, *, doc_type: str, mime_type: str, size_bytes: int,
    ) -> PresignedUpload:
        await self._require_provider(user)

        if doc_type not in VALID_DOCUMENT_TYPES:
            raise DocumentServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"type must be one of {sorted(VALID_DOCUMENT_TYPES)}",
            )
        if mime_type not in ALLOWED_DOCUMENT_MIME_TYPES:
            raise DocumentServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"mime_type must be one of {sorted(ALLOWED_DOCUMENT_MIME_TYPES)}",
            )
        if size_bytes <= 0 or size_bytes > MAX_DOCUMENT_SIZE_BYTES:
            raise DocumentServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"size_bytes must be in 1..{MAX_DOCUMENT_SIZE_BYTES}",
            )

        ext = _MIME_TO_EXT.get(mime_type, "bin")
        token = secrets.token_urlsafe(16)
        # `documents/{user_id}/{type}/{token}.{ext}` — embeds the
        # category so the worker scanning by type can short-circuit
        # via S3 prefix listing later if we ever audit storage usage.
        key = f"documents/{user.id}/{doc_type}/{token}.{ext}"

        return await self._adapter.generate_upload_url(
            key,
            mime=mime_type,
            max_size=MAX_DOCUMENT_SIZE_BYTES,
            ttl_seconds=3600,
        )

    # ─── confirm ────────────────────────────────────────────────────────────

    async def confirm_upload(
        self,
        user: User,
        s3_key: str,
        doc_type: str,
        title: str | None,
        expires_at: date | None,
    ) -> Document:
        await self._require_provider(user)

        if doc_type not in VALID_DOCUMENT_TYPES:
            raise DocumentServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"type must be one of {sorted(VALID_DOCUMENT_TYPES)}",
            )

        if not s3_key.startswith(f"documents/{user.id}/"):
            raise DocumentServiceError(
                status.HTTP_403_FORBIDDEN,
                "permission_denied",
                "s3_key does not belong to this user.",
            )

        try:
            meta = await self._adapter.head_object(s3_key)
        except ObjectNotFound:
            raise DocumentServiceError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "Upload not found at the requested key. Did the PUT succeed?",
            )

        if meta.content_type and meta.content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
            await self._adapter.delete_object(s3_key)
            raise DocumentServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"Uploaded content_type {meta.content_type!r} is not an allowed document type.",
            )

        if meta.size > MAX_DOCUMENT_SIZE_BYTES:
            await self._adapter.delete_object(s3_key)
            raise DocumentServiceError(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "payload_too_large",
                f"Uploaded file exceeds the {MAX_DOCUMENT_SIZE_BYTES}-byte limit.",
            )

        row = Document(
            user_id=user.id,
            type=doc_type,
            title=title,
            s3_key=s3_key,
            mime_type=meta.content_type,
            size_bytes=meta.size,
            expires_at=expires_at,
        )
        self.db.add(row)
        await self.db.flush()

        await self.audit_repo.log(
            action=AuditAction.DOCUMENT_UPLOADED,
            entity_type="document",
            entity_id=str(row.id),
            actor_id=user.id,
            new_value={
                "type": doc_type,
                "title": title,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
            audit_ctx=self.audit_ctx,
        )
        return row

    # ─── delete ─────────────────────────────────────────────────────────────

    async def delete(self, user: User, doc_id: uuid.UUID) -> None:
        await self._require_provider(user)
        row, _ = await self.get_or_404(user, doc_id)
        s3_key = row.s3_key
        doc_type = row.type

        row.is_deleted = True
        row.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self.audit_repo.log(
            action=AuditAction.DOCUMENT_DELETED,
            entity_type="document",
            entity_id=str(doc_id),
            actor_id=user.id,
            old_value={"type": doc_type, "s3_key": s3_key},
            audit_ctx=self.audit_ctx,
        )

        # Best-effort cleanup of the bytes in the private bucket.
        # Compliance copies of KYC docs may need to be kept for legal
        # reasons in some jurisdictions — when that requirement is
        # confirmed we can swap this to soft-delete-only and let a
        # retention worker hard-delete on schedule.
        try:
            await self._adapter.delete_object(s3_key)
        except Exception as exc:
            logger.warning(
                "provider_documents: drop %s failed: %s", s3_key, exc,
            )

    # ─── Internal ───────────────────────────────────────────────────────────

    async def _sign_download(self, s3_key: str | None) -> str | None:
        if not s3_key:
            return None
        try:
            return await self._adapter.generate_download_url(
                s3_key, ttl_seconds=_DOWNLOAD_TTL_SECONDS,
            )
        except Exception as exc:
            logger.warning(
                "provider_documents: failed to sign download URL for %s: %s",
                s3_key, exc,
            )
            return None


def get_provider_documents_service(
    db: AsyncSession, request,
) -> ProviderDocumentsService:
    return ProviderDocumentsService(db=db, audit_ctx=get_audit_context(request))
