"""
domains/users/provider_documents_router.py — /api/v1/users/me/
provider-documents (Phase 5 chunk Y4).

Endpoints per plan §2.12:
  GET    /me/provider-documents                list + freshly-signed
                                                download URLs (1 h TTL)
  POST   /me/provider-documents/upload-url     presigned PUT
  POST   /me/provider-documents                confirm + INSERT
  DELETE /me/provider-documents/{doc_id}       step-up; soft-delete + S3

DELETE is step-up gated because removing a KYC artifact could be the
last action before an attacker tries to re-submit a forged one to
defeat compliance checks. Upload + list don't need step-up — they're
routine onboarding flows.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.core.step_up import require_step_up
from domains.auth.service import get_current_user
from domains.users.models import User
from domains.users.provider_documents_schemas import (
    DocumentConfirmRequest,
    DocumentResponse,
    DocumentUploadUrlRequest,
    DocumentUploadUrlResponse,
)
from domains.users.provider_documents_service import (
    get_provider_documents_service,
)
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(
    prefix="/api/v1/users/me/provider-documents",
    tags=["User Provider Documents"],
)


def _to_response(doc, download_url) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        user_id=doc.user_id,
        type=doc.type,
        title=doc.title,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        expires_at=doc.expires_at,
        download_url=download_url,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


# ─── List ────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=Envelope[list[DocumentResponse]],
    summary="List the caller's KYC documents with short-TTL signed "
            "download URLs (1 h).",
    responses={
        409: {"description": "Provider mode not active — activate first."},
    },
)
async def list_documents(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[DocumentResponse]]:
    service = get_provider_documents_service(db, request)
    rows = await service.list_for_user(current_user)
    return Envelope[list[DocumentResponse]](
        data=[_to_response(d, url) for d, url in rows]
    )


# ─── upload-url ──────────────────────────────────────────────────────────────


@router.post(
    "/upload-url",
    response_model=Envelope[DocumentUploadUrlResponse],
    summary="Step 1 of document upload — returns a presigned PUT URL "
            "targeting the private bucket. The caller declares the doc type "
            "up front so the key embeds it.",
    responses={
        409: {"description": "Provider mode not active."},
        422: {"description": "type / mime_type / size_bytes outside allowed range."},
    },
)
async def upload_url(
    request: Request,
    body: DocumentUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[DocumentUploadUrlResponse]:
    service = get_provider_documents_service(db, request)
    presigned = await service.prepare_upload(
        current_user,
        doc_type=body.type,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
    )
    return Envelope[DocumentUploadUrlResponse](
        data=DocumentUploadUrlResponse(
            url=presigned.url,
            method=presigned.method,
            headers=presigned.headers,
            s3_key=presigned.s3_key,
            expires_in=presigned.expires_in,
        )
    )


# ─── Confirm ─────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=Envelope[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Step 2: confirm a document upload — HEADs the bytes, validates "
            "mime + size, INSERTs the Document row, and audits "
            "DOCUMENT_UPLOADED.",
    responses={
        403: {"description": "s3_key does not belong to this user."},
        404: {"description": "Upload not found at the requested key."},
        422: {"description": "type, mime or size violated server rules."},
    },
)
async def confirm(
    request: Request,
    body: DocumentConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[DocumentResponse]:
    service = get_provider_documents_service(db, request)
    doc = await service.confirm_upload(
        current_user, body.s3_key, body.type, body.title, body.expires_at,
    )
    await db.commit()
    # Re-sign the download URL for the response — same lifecycle as the
    # listing endpoint so the frontend never has to special-case.
    download_url = await service._sign_download(doc.s3_key)
    return Envelope[DocumentResponse](data=_to_response(doc, download_url))


# ─── Delete ──────────────────────────────────────────────────────────────────


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Step-up gated. Soft-deletes the local row and best-effort "
            "drops the bytes from the private bucket. The user-facing list "
            "reflects the removal immediately even if S3 cleanup fails.",
    responses={
        401: {"description": "Step-up auth required."},
        404: {"description": "Document not found."},
    },
)
async def delete_document(
    request: Request,
    doc_id: uuid.UUID = Path(...),
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = get_provider_documents_service(db, request)
    await service.delete(current_user, doc_id)
    await db.commit()
