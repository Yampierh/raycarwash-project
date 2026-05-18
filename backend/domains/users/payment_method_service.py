"""
domains/users/payment_method_service.py — orchestration for
`/api/v1/users/me/payment-methods` (Phase 4 chunk U).

Three layers of responsibility:

  1. User-facing operations called from the router:
     - create_setup_intent → returns client_secret to the SDK.
     - list / get / set_default / delete.

  2. Webhook-driven sync (called from the existing payments webhook
     router):
     - upsert_from_attached_event — first time we see a PM.
     - update_from_updated_event — card expiration moved, billing zip
       changed, etc.
     - mark_detached_event — user revoked at Stripe Dashboard, or our
       own server-side detach echoed back.

  3. Stripe Customer bootstrap — delegates to the existing
     PaymentService._get_or_create_stripe_customer so we keep ONE place
     that knows how to mint a `cus_*` ID. Otherwise the two domains
     could race and create duplicate customers for the same user.

Default-flip semantics mirror AddressService:
  - first card added auto-defaults.
  - deleting the default auto-promotes the next.
  - set_default_atomic respects the partial unique index.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_payment_method_adapter
from app.middleware.audit_context import AuditContext, get_audit_context
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.payments.service import PaymentService
from domains.users.models import User
from domains.users.payment_method import PaymentMethod
from domains.users.payment_method_repository import PaymentMethodRepository
from infrastructure.payments.base import (
    PaymentAdapterError,
    PaymentMethodSnapshot,
    SetupIntentResult,
)

logger = logging.getLogger(__name__)


class PaymentMethodService:
    def __init__(self, db: AsyncSession, audit_ctx: AuditContext) -> None:
        self.db = db
        self.audit_ctx = audit_ctx
        self.repo = PaymentMethodRepository(db)
        self.audit_repo = AuditRepository(db)
        self._adapter = get_payment_method_adapter()

    # ─── User-facing reads ──────────────────────────────────────────────────

    async def list_for_user(self, user: User) -> list[PaymentMethod]:
        return list(await self.repo.list_active(user.id))

    async def get_or_404(
        self, user: User, pm_id: uuid.UUID
    ) -> PaymentMethod:
        row = await self.repo.get_by_id(user.id, pm_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "resource_not_found",
                    "message": "Payment method not found.",
                },
            )
        return row

    # ─── User-facing writes ─────────────────────────────────────────────────

    async def create_setup_intent(
        self, user: User, *, idempotency_key: str | None = None
    ) -> SetupIntentResult:
        """Mint a SetupIntent so the frontend can attach a card via the
        Stripe SDK. The actual PaymentMethod row is written later by the
        webhook handler — we only return the secret here."""
        customer_id = await self._ensure_stripe_customer(user)
        try:
            return await self._adapter.create_setup_intent(
                customer_id=customer_id,
                idempotency_key=idempotency_key,
            )
        except PaymentAdapterError as exc:
            logger.warning("setup_intent: adapter failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "service_unavailable",
                    "message": "Payment provider is currently unavailable.",
                },
            )

    async def set_default(
        self, user: User, pm_id: uuid.UUID
    ) -> PaymentMethod:
        ok = await self.repo.set_default_atomic(user.id, pm_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "resource_not_found",
                    "message": "Payment method not found.",
                },
            )
        await self.db.flush()
        await self.audit_repo.log(
            action=AuditAction.PAYMENT_METHOD_DEFAULT,
            entity_type="payment_method",
            entity_id=str(pm_id),
            actor_id=user.id,
            new_value={"is_default": True},
            audit_ctx=self.audit_ctx,
        )
        return await self.get_or_404(user, pm_id)

    async def delete(self, user: User, pm_id: uuid.UUID) -> None:
        row = await self.get_or_404(user, pm_id)
        was_default = bool(row.is_default)
        stripe_pm_id = row.stripe_payment_method_id

        # Soft-delete LOCALLY first so the user-facing list reflects the
        # removal immediately. Stripe detach runs after, and on adapter
        # failure we still keep the local soft-delete: the user wants
        # the card gone from the app, and a leftover Stripe PM is a
        # housekeeping issue not a UX issue. The webhook (payment_method.
        # detached) will re-converge if it ever lands later.
        await self.repo.soft_delete(
            user.id, pm_id, now=datetime.now(timezone.utc)
        )

        if was_default:
            replacement = await self.repo.first_active(
                user.id, exclude_id=pm_id
            )
            if replacement is not None:
                replacement.is_default = True
                await self.db.flush()

        await self.audit_repo.log(
            action=AuditAction.PAYMENT_METHOD_REMOVED,
            entity_type="payment_method",
            entity_id=str(pm_id),
            actor_id=user.id,
            old_value={
                "stripe_payment_method_id": stripe_pm_id,
                "was_default": was_default,
            },
            audit_ctx=self.audit_ctx,
        )

        try:
            await self._adapter.detach_payment_method(
                stripe_payment_method_id=stripe_pm_id
            )
        except PaymentAdapterError as exc:
            # Non-fatal — the local view is already correct. Log loudly
            # so ops can reconcile if it persists.
            logger.warning(
                "payment_method.detach failed for pm=%s — local soft-delete kept: %s",
                stripe_pm_id, exc,
            )

    # ─── Webhook entry points ───────────────────────────────────────────────

    async def upsert_from_snapshot(
        self,
        *,
        user_id: uuid.UUID,
        snapshot: PaymentMethodSnapshot,
    ) -> PaymentMethod:
        """Idempotent insert-or-update from a Stripe payment_method.{attached,
        updated} payload. Webhook handler delivers (user_id, snapshot);
        we reconcile.

        The first card a user adds auto-defaults — matches AddressService.
        """
        existing = await self.repo.get_by_stripe_id(
            snapshot.stripe_payment_method_id
        )
        if existing is not None:
            existing.type = snapshot.type
            existing.brand = snapshot.brand
            existing.last4 = snapshot.last4
            existing.exp_month = snapshot.exp_month
            existing.exp_year = snapshot.exp_year
            existing.billing_zip = snapshot.billing_zip
            # If it was previously soft-deleted (re-attach), revive it.
            if existing.is_deleted:
                existing.is_deleted = False
                existing.deleted_at = None
            await self.db.flush()
            return existing

        is_first = (await self.repo.count_active(user_id)) == 0
        row = PaymentMethod(
            user_id=user_id,
            stripe_payment_method_id=snapshot.stripe_payment_method_id,
            type=snapshot.type,
            brand=snapshot.brand,
            last4=snapshot.last4,
            exp_month=snapshot.exp_month,
            exp_year=snapshot.exp_year,
            billing_zip=snapshot.billing_zip,
            is_default=is_first,
        )
        self.repo.add(row)
        await self.db.flush()

        await self.audit_repo.log(
            action=AuditAction.PAYMENT_METHOD_ADDED,
            entity_type="payment_method",
            entity_id=str(row.id),
            actor_id=user_id,
            new_value={
                "stripe_payment_method_id": snapshot.stripe_payment_method_id,
                "brand": snapshot.brand,
                "last4": snapshot.last4,
                "is_default": row.is_default,
            },
            audit_ctx=self.audit_ctx,
        )
        return row

    async def mark_detached_by_stripe_id(
        self, *, stripe_payment_method_id: str
    ) -> bool:
        """Webhook payment_method.detached path. Returns True iff a local
        row was actually flipped (false = unknown PM, ignore safely)."""
        ok = await self.repo.soft_delete_by_stripe_id(
            stripe_payment_method_id,
            now=datetime.now(timezone.utc),
        )
        if ok:
            # Audit without an actor — webhook events lack a user
            # session context. AuditAction.PAYMENT_METHOD_REMOVED is the
            # closest fit; we record the metadata so reconciliation can
            # trace it.
            await self.audit_repo.log(
                action=AuditAction.PAYMENT_METHOD_REMOVED,
                entity_type="payment_method",
                entity_id=stripe_payment_method_id,
                actor_id=None,
                metadata={"source": "stripe_webhook"},
                old_value={"stripe_payment_method_id": stripe_payment_method_id},
                audit_ctx=self.audit_ctx,
            )
        return ok

    # ─── Internal helpers ───────────────────────────────────────────────────

    async def _ensure_stripe_customer(self, user: User) -> str:
        """Delegate to the existing PaymentService so we don't end up
        with two pieces of code minting cus_* IDs for the same user."""
        return await PaymentService(self.db)._get_or_create_stripe_customer(user)


def get_payment_method_service(db: AsyncSession, request) -> PaymentMethodService:
    return PaymentMethodService(db=db, audit_ctx=get_audit_context(request))


def get_publishable_key() -> str:
    """Surface the publishable key so the SDK can confirm the SetupIntent
    on the frontend. Kept in this module so the router doesn't have to
    reach into settings directly."""
    return get_settings().STRIPE_PUBLISHABLE_KEY
