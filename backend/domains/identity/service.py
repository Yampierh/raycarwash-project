from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.identity.models import IdentityVerification, KycStatus


class IdentityService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def submit_documents(
        self,
        user_id,
        document_data: dict,
        verification_provider: str | None = None,
    ) -> IdentityVerification:
        stmt = select(IdentityVerification).where(
            IdentityVerification.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        identity = result.scalar_one_or_none()

        if identity is None:
            identity = IdentityVerification(
                user_id=user_id,
                status=KycStatus.SUBMITTED.value,
                document_data=document_data,
                verification_provider=verification_provider,
            )
            self.db.add(identity)
        else:
            identity.status = KycStatus.SUBMITTED.value
            identity.document_data = document_data
            if verification_provider:
                identity.verification_provider = verification_provider
            identity.rejection_reason = None

        await self.db.flush()
        return identity

    async def get_verification(self, user_id) -> IdentityVerification | None:
        stmt = select(IdentityVerification).where(
            IdentityVerification.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def approve_kyc(self, user_id) -> IdentityVerification:
        stmt = select(IdentityVerification).where(
            IdentityVerification.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="KYC record not found.",
            )
        record.status = KycStatus.APPROVED.value
        record.rejection_reason = None
        return record

    async def reject_kyc(self, user_id, reason: str) -> IdentityVerification:
        stmt = select(IdentityVerification).where(
            IdentityVerification.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="KYC record not found.",
            )
        record.status = KycStatus.REJECTED.value
        record.rejection_reason = reason
        return record
