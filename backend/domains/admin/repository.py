from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import (
    Permission,
    Role,
    RolePermission,
    UserRoleAssociation,
)
from domains.users.models import User
from domains.appointments.models import Appointment, AppointmentStatus
from domains.providers.models import ProviderProfile
from domains.payments.models import PaymentLedger, Refund
from domains.locations.models import City
from domains.reviews.models import Review
from domains.audit.models import AuditLog, AuditAction
from domains.credits.models import CustomerCredit


class AdminRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Users ──────────────────────────────────────────────────────── #

    async def list_users(
        self,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        role_filter: str | None = None,
    ) -> tuple[list[User], int]:
        """Paginated user list with optional search and role filter."""
        base = (
            select(User)
            .where(User.is_deleted.is_(False))
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRoleAssociation.role)
                .selectinload(Role.permissions)
            )
            .execution_options(populate_existing=True)
        )

        if search:
            base = base.where(User.email.ilike(f"%{search}%"))

        if role_filter:
            base = base.join(
                UserRoleAssociation, UserRoleAssociation.user_id == User.id
            ).join(Role, Role.id == UserRoleAssociation.role_id).where(
                Role.name == role_filter
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = base.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_user_with_roles(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id, User.is_deleted.is_(False))
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRoleAssociation.role)
                .selectinload(Role.permissions)
            )
            .execution_options(populate_existing=True)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def set_user_active(self, user_id: uuid.UUID, is_active: bool) -> bool:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=is_active, updated_at=datetime.now(timezone.utc))
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

    async def assign_role_to_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID,
    ) -> bool:
        """Assign a role to a user. Idempotent — no error if already assigned."""
        existing = await self._db.execute(
            select(UserRoleAssociation).where(
                UserRoleAssociation.user_id == user_id,
                UserRoleAssociation.role_id == role_id,
            )
        )
        if existing.scalar_one_or_none():
            return False

        self._db.add(UserRoleAssociation(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
        ))
        await self._db.flush()
        return True

    async def revoke_role_from_user(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        stmt = delete(UserRoleAssociation).where(
            UserRoleAssociation.user_id == user_id,
            UserRoleAssociation.role_id == role_id,
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

    # ── Roles ──────────────────────────────────────────────────────── #

    async def list_roles(self) -> list[Role]:
        stmt = (
            select(Role)
            .where(Role.is_deleted.is_(False))
            .options(selectinload(Role.permissions))
            .order_by(Role.name)
            .execution_options(populate_existing=True)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.id == role_id, Role.is_deleted.is_(False))
            .options(selectinload(Role.permissions))
            .execution_options(populate_existing=True)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name, Role.is_deleted.is_(False))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_role(self, name: str, description: str | None = None) -> Role:
        role = Role(name=name, description=description, is_system=False)
        self._db.add(role)
        await self._db.flush()
        # Re-fetch with permissions eager-loaded so RoleRead can serialize
        return await self.get_role_by_id(role.id)  # type: ignore[return-value]

    async def update_role(self, role_id: uuid.UUID, fields: dict) -> Role | None:
        role = await self.get_role_by_id(role_id)
        if role is None or role.is_system:
            return None
        for key, value in fields.items():
            setattr(role, key, value)
        await self._db.flush()
        # Re-fetch so updated fields + permissions are fresh
        return await self.get_role_by_id(role_id)

    async def delete_role(self, role_id: uuid.UUID) -> bool:
        """Soft-delete a role. Refuses to delete system roles."""
        role = await self.get_role_by_id(role_id)
        if role is None:
            return False
        if role.is_system:
            raise ValueError(f"System role '{role.name}' cannot be deleted.")
        role.is_deleted = True
        role.deleted_at = datetime.now(timezone.utc)
        await self._db.flush()
        return True

    async def assign_permission_to_role(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> bool:
        """Idempotent — no error if already assigned."""
        existing = await self._db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        if existing.scalar_one_or_none():
            return False
        self._db.add(RolePermission(role_id=role_id, permission_id=permission_id))
        await self._db.flush()
        return True

    async def revoke_permission_from_role(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> bool:
        stmt = delete(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

    # ── Permissions ────────────────────────────────────────────────── #

    async def list_permissions(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.resource, Permission.action)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_permission_by_id(self, permission_id: uuid.UUID) -> Permission | None:
        stmt = select(Permission).where(Permission.id == permission_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_permission(
        self,
        name: str,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> Permission:
        perm = Permission(name=name, resource=resource, action=action, description=description)
        self._db.add(perm)
        await self._db.flush()
        await self._db.refresh(perm)
        return perm

    async def delete_permission(self, permission_id: uuid.UUID) -> bool:
        perm = await self.get_permission_by_id(permission_id)
        if perm is None:
            return False
        await self._db.execute(
            delete(RolePermission).where(RolePermission.permission_id == permission_id)
        )
        await self._db.execute(delete(Permission).where(Permission.id == permission_id))
        await self._db.flush()
        return True

    # ── Appointments ───────────────────────────────────────────────── #

    async def list_appointments(
        self,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        base = select(Appointment).where(Appointment.is_deleted.is_(False))

        if status:
            base = base.where(Appointment.status == status)
        if start_date:
            base = base.where(Appointment.scheduled_time >= start_date)
        if end_date:
            base = base.where(Appointment.scheduled_time <= end_date)
        if search:
            matching_users = select(User.id).where(User.email.ilike(f"%{search}%")).subquery()
            base = base.where(
                (Appointment.client_id.in_(select(matching_users.c.id))) |
                (Appointment.detailer_id.in_(select(matching_users.c.id)))
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(Appointment.scheduled_time.desc()).offset((page - 1) * per_page).limit(per_page)
        result = await self._db.execute(stmt)
        appointments = list(result.scalars().all())

        rows = []
        for appt in appointments:
            client_email = None
            detailer_email = None
            service_name = None
            if appt.client_id:
                r = await self._db.execute(select(User.email).where(User.id == appt.client_id))
                client_email = r.scalar_one_or_none()
            if appt.detailer_id:
                r = await self._db.execute(select(User.email).where(User.id == appt.detailer_id))
                detailer_email = r.scalar_one_or_none()
            if appt.service_id:
                from domains.services_catalog.models import Service
                r = await self._db.execute(select(Service.name).where(Service.id == appt.service_id))
                service_name = r.scalar_one_or_none()
            rows.append({
                "id": appt.id,
                "status": appt.status,
                "scheduled_time": appt.scheduled_time,
                "client_email": client_email,
                "detailer_email": detailer_email,
                "service_name": service_name,
                "estimated_price": appt.estimated_price,
                "actual_price": appt.actual_price,
                "client_notes": appt.client_notes,
                "detailer_notes": appt.detailer_notes,
                "service_address": appt.service_address,
                "stripe_payment_intent_id": appt.stripe_payment_intent_id,
                "arrived_at": appt.arrived_at,
                "started_at": appt.started_at,
                "completed_at": appt.completed_at,
                "created_at": appt.created_at,
                "updated_at": appt.updated_at,
            })
        return rows, total

    async def get_appointment_detail(self, appointment_id: uuid.UUID) -> dict | None:
        stmt = select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        appt = result.scalar_one_or_none()
        if appt is None:
            return None

        client_email = None
        detailer_email = None
        service_name = None
        if appt.client_id:
            r = await self._db.execute(select(User.email).where(User.id == appt.client_id))
            client_email = r.scalar_one_or_none()
        if appt.detailer_id:
            r = await self._db.execute(select(User.email).where(User.id == appt.detailer_id))
            detailer_email = r.scalar_one_or_none()
        if appt.service_id:
            from domains.services_catalog.models import Service
            r = await self._db.execute(select(Service.name).where(Service.id == appt.service_id))
            service_name = r.scalar_one_or_none()

        return {
            "id": appt.id,
            "status": appt.status,
            "scheduled_time": appt.scheduled_time,
            "client_email": client_email,
            "detailer_email": detailer_email,
            "service_name": service_name,
            "estimated_price": appt.estimated_price,
            "actual_price": appt.actual_price,
            "client_notes": appt.client_notes,
            "detailer_notes": appt.detailer_notes,
            "service_address": appt.service_address,
            "stripe_payment_intent_id": appt.stripe_payment_intent_id,
            "arrived_at": appt.arrived_at,
            "started_at": appt.started_at,
            "completed_at": appt.completed_at,
            "created_at": appt.created_at,
            "updated_at": appt.updated_at,
        }

    async def force_appointment_status(
        self,
        appointment_id: uuid.UUID,
        new_status: str,
        actor_id: uuid.UUID,
    ) -> bool:
        stmt = (
            update(Appointment)
            .where(Appointment.id == appointment_id, Appointment.is_deleted.is_(False))
            .values(status=new_status, updated_at=datetime.now(timezone.utc))
        )
        result = await self._db.execute(stmt)
        if result.rowcount == 0:
            return False
        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.APPOINTMENT_STATUS_CHANGED,
            entity_type="appointment",
            entity_id=str(appointment_id),
            metadata_={"forced_status": new_status, "by": "admin"},
        ))
        await self._db.flush()
        return True

    # ── Verifications ─────────────────────────────────────────────── #

    async def list_verifications(self, status_filter: str | None = None) -> list[dict]:
        stmt = select(ProviderProfile)
        if status_filter:
            stmt = stmt.where(ProviderProfile.verification_status == status_filter)
        else:
            stmt = stmt.where(ProviderProfile.verification_status != "not_submitted")
        stmt = stmt.order_by(ProviderProfile.verification_submitted_at.asc().nullslast())
        result = await self._db.execute(stmt)
        profiles = list(result.scalars().all())

        rows = []
        for p in profiles:
            r = await self._db.execute(select(User.email).where(User.id == p.user_id))
            user_email = r.scalar_one_or_none()
            rows.append({
                "provider_id": p.id,
                "user_email": user_email,
                "legal_full_name": p.legal_full_name,
                "verification_status": p.verification_status,
                "background_check_consent": p.background_check_consent,
                "submitted_at": p.verification_submitted_at,
                "reviewed_at": p.verification_reviewed_at,
                "rejection_reason": p.rejection_reason,
            })
        return rows

    async def approve_verification(self, provider_id: uuid.UUID, actor_id: uuid.UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(ProviderProfile)
            .where(ProviderProfile.id == provider_id)
            .values(
                verification_status="approved",
                verification_reviewed_at=now,
                rejection_reason=None,
                updated_at=now,
            )
        )
        result = await self._db.execute(stmt)
        if result.rowcount == 0:
            return False
        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.DETAILER_PROFILE_UPDATED,
            entity_type="provider_profile",
            entity_id=str(provider_id),
            metadata_={"action": "verification_approved"},
        ))
        await self._db.flush()
        return True

    async def reject_verification(self, provider_id: uuid.UUID, reason: str, actor_id: uuid.UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(ProviderProfile)
            .where(ProviderProfile.id == provider_id)
            .values(
                verification_status="rejected",
                verification_reviewed_at=now,
                rejection_reason=reason,
                updated_at=now,
            )
        )
        result = await self._db.execute(stmt)
        if result.rowcount == 0:
            return False
        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.DETAILER_PROFILE_UPDATED,
            entity_type="provider_profile",
            entity_id=str(provider_id),
            metadata_={"action": "verification_rejected", "reason": reason},
        ))
        await self._db.flush()
        return True

    # ── Detailers (Plan 24 W2-C) ──────────────────────────────────── #

    # application_status FSM gates. Keep these in sync with the docstring
    # on ProviderProfile.application_status (domains/providers/models.py).
    _APPROVABLE_FROM = frozenset({
        "submitted", "bg_check_pending", "docs_review", "suspended",
    })
    _SUSPENDABLE_FROM = frozenset({"approved"})

    async def _get_provider_with_email(
        self, provider_id: uuid.UUID,
    ) -> tuple[ProviderProfile, str | None] | None:
        stmt = select(ProviderProfile).where(ProviderProfile.id == provider_id)
        profile = (await self._db.execute(stmt)).scalar_one_or_none()
        if profile is None:
            return None
        email_row = await self._db.execute(
            select(User.email).where(User.id == profile.user_id)
        )
        return profile, email_row.scalar_one_or_none()

    async def approve_detailer(
        self,
        provider_id: uuid.UUID,
        actor_id: uuid.UUID,
        notes: str | None = None,
    ) -> tuple[str, str, str | None] | None:
        """Transition application_status → approved. Returns
        (previous_status, new_status, user_email) or None if the profile
        doesn't exist. Raises ValueError on FSM violation."""
        found = await self._get_provider_with_email(provider_id)
        if found is None:
            return None
        profile, user_email = found

        prev = profile.application_status
        if prev not in self._APPROVABLE_FROM:
            raise ValueError(
                f"Cannot approve from application_status='{prev}'. "
                f"Allowed source states: {sorted(self._APPROVABLE_FROM)}"
            )

        now = datetime.now(timezone.utc)
        profile.application_status = "approved"
        profile.verification_reviewed_at = now
        profile.rejection_reason = None
        profile.updated_at = now

        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.PROVIDER_STATUS_CHANGED,
            entity_type="provider_profile",
            entity_id=str(provider_id),
            old_value={"application_status": prev},
            new_value={"application_status": "approved"},
            metadata_={"action": "detailer_approved", "notes": notes} if notes else {"action": "detailer_approved"},
        ))
        await self._db.flush()
        return prev, "approved", user_email

    async def suspend_detailer(
        self,
        provider_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str,
    ) -> tuple[str, str, str | None] | None:
        """Transition application_status approved → suspended. Returns
        (previous_status, new_status, user_email) or None if the profile
        doesn't exist. Raises ValueError on FSM violation."""
        found = await self._get_provider_with_email(provider_id)
        if found is None:
            return None
        profile, user_email = found

        prev = profile.application_status
        if prev not in self._SUSPENDABLE_FROM:
            raise ValueError(
                f"Cannot suspend from application_status='{prev}'. "
                f"Allowed source states: {sorted(self._SUSPENDABLE_FROM)}"
            )

        now = datetime.now(timezone.utc)
        profile.application_status = "suspended"
        profile.verification_reviewed_at = now
        profile.rejection_reason = reason
        profile.updated_at = now

        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.PROVIDER_STATUS_CHANGED,
            entity_type="provider_profile",
            entity_id=str(provider_id),
            old_value={"application_status": prev},
            new_value={"application_status": "suspended"},
            metadata_={"action": "detailer_suspended", "reason": reason},
        ))
        await self._db.flush()
        return prev, "suspended", user_email

    # ── Reviews moderation (Plan 24 W2-D) ─────────────────────────── #

    # Static profanity / red-flag keywords. Case-insensitive substring
    # match against Review.comment. Keep this list short and obvious —
    # false positives are worse than false negatives at this stage; admins
    # see the rating signal regardless.
    _FLAG_KEYWORDS: tuple[str, ...] = (
        "scam", "fraud", "stole", "thief", "stolen", "racist",
    )
    _LOW_RATING_THRESHOLD: int = 2

    _APPROVE_REVIEW_FROM = frozenset({"auto_pending"})
    _HIDE_REVIEW_FROM = frozenset({"auto_pending", "approved"})

    @classmethod
    def _compute_review_flags(cls, rating: int, comment: str | None) -> list[str]:
        reasons: list[str] = []
        if rating <= cls._LOW_RATING_THRESHOLD:
            reasons.append("low_rating")
        if comment:
            lowered = comment.lower()
            for kw in cls._FLAG_KEYWORDS:
                if kw in lowered:
                    reasons.append(f"keyword:{kw}")
        return reasons

    async def list_review_queue(self) -> list[dict]:
        """Returns auto_pending reviews that match at least one flag rule.
        Order by created_at ASC (oldest first — first-in-first-out)."""
        stmt = (
            select(Review)
            .where(Review.moderation_state == "auto_pending")
            .order_by(Review.created_at.asc())
        )
        rows = list((await self._db.execute(stmt)).scalars().all())

        results: list[dict] = []
        for r in rows:
            reasons = self._compute_review_flags(r.rating, r.comment)
            if not reasons:
                continue  # auto_pending but no rule fires → don't surface

            reviewer_email = (
                await self._db.execute(select(User.email).where(User.id == r.reviewer_id))
            ).scalar_one_or_none()
            detailer_email = (
                await self._db.execute(select(User.email).where(User.id == r.detailer_id))
            ).scalar_one_or_none()
            results.append({
                "review_id": r.id,
                "appointment_id": r.appointment_id,
                "reviewer_email": reviewer_email,
                "detailer_email": detailer_email,
                "rating": r.rating,
                "comment": r.comment,
                "flag_reasons": reasons,
                "created_at": r.created_at,
            })
        return results

    async def approve_review(
        self, review_id: uuid.UUID, actor_id: uuid.UUID, note: str | None = None,
    ) -> tuple[str, str] | None:
        """Mark review as approved (keep visible). Returns
        (previous_state, new_state) or None if the review doesn't exist.
        Raises ValueError on FSM violation."""
        review = (await self._db.execute(
            select(Review).where(Review.id == review_id)
        )).scalar_one_or_none()
        if review is None:
            return None
        prev = review.moderation_state
        if prev not in self._APPROVE_REVIEW_FROM:
            raise ValueError(
                f"Cannot approve from moderation_state='{prev}'. "
                f"Allowed source states: {sorted(self._APPROVE_REVIEW_FROM)}"
            )
        now = datetime.now(timezone.utc)
        review.moderation_state = "approved"
        review.moderation_actor_id = actor_id
        review.moderation_acted_at = now
        review.moderation_note = note

        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.REVIEW_MODERATED,
            entity_type="review",
            entity_id=str(review_id),
            old_value={"moderation_state": prev},
            new_value={"moderation_state": "approved"},
            metadata_={"action": "review_approved", "note": note} if note else {"action": "review_approved"},
        ))
        await self._db.flush()
        return prev, "approved"

    async def hide_review(
        self, review_id: uuid.UUID, actor_id: uuid.UUID, note: str,
    ) -> tuple[str, str] | None:
        """Mark review as hidden. Returns (previous_state, new_state) or
        None if the review doesn't exist. Raises ValueError on FSM
        violation."""
        review = (await self._db.execute(
            select(Review).where(Review.id == review_id)
        )).scalar_one_or_none()
        if review is None:
            return None
        prev = review.moderation_state
        if prev not in self._HIDE_REVIEW_FROM:
            raise ValueError(
                f"Cannot hide from moderation_state='{prev}'. "
                f"Allowed source states: {sorted(self._HIDE_REVIEW_FROM)}"
            )
        now = datetime.now(timezone.utc)
        review.moderation_state = "hidden"
        review.moderation_actor_id = actor_id
        review.moderation_acted_at = now
        review.moderation_note = note

        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.REVIEW_MODERATED,
            entity_type="review",
            entity_id=str(review_id),
            old_value={"moderation_state": prev},
            new_value={"moderation_state": "hidden"},
            metadata_={"action": "review_hidden", "note": note},
        ))
        await self._db.flush()
        return prev, "hidden"

    # ── Appointments: refund + reassign (Plan 24 W2-B) ────────────── #

    # States that allow reassignment — must not yet be in active service.
    _REASSIGNABLE_STATUSES = frozenset({
        AppointmentStatus.PENDING,
        AppointmentStatus.SEARCHING,
        AppointmentStatus.NO_DETAILER_FOUND,
        AppointmentStatus.CONFIRMED,
    })

    @staticmethod
    def _appointment_max_refundable_cents(appt: Appointment) -> int:
        """The cap for a refund. Prefer actual_price (post-completion total)
        else the estimated price."""
        return int(appt.actual_price or appt.estimated_price)

    async def refund_appointment(
        self,
        *,
        appointment_id: uuid.UUID,
        actor_id: uuid.UUID,
        amount_cents: int,
        reason: str,
        note: str | None,
    ) -> tuple[Refund, str | None] | None:
        """Persist a Refund row + issue the Stripe refund via PaymentService.

        Returns (refund, stripe_refund_id) or None if the appointment
        doesn't exist. Raises ValueError on FSM / business-rule violations
        (no PaymentIntent, amount exceeds cap, already fully refunded).
        """
        appt = (await self._db.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if appt is None:
            return None
        if not appt.stripe_payment_intent_id:
            raise ValueError("Appointment has no PaymentIntent; nothing to refund.")

        max_refundable = self._appointment_max_refundable_cents(appt)
        prior_refunded_stmt = (
            select(func.coalesce(func.sum(Refund.amount_cents), 0))
            .where(
                Refund.appointment_id == appointment_id,
                Refund.status != "failed",
            )
        )
        prior_refunded = int(
            (await self._db.execute(prior_refunded_stmt)).scalar_one()
        )
        if prior_refunded + amount_cents > max_refundable:
            raise ValueError(
                f"Refund cap exceeded: prior={prior_refunded}¢, "
                f"requested={amount_cents}¢, cap={max_refundable}¢."
            )

        # Issue via Stripe (auto-stub in tests / dev).
        from domains.payments.service import PaymentService

        payment_service = PaymentService(self._db)
        stripe_refund_id = await payment_service.create_refund(
            payment_intent_id=appt.stripe_payment_intent_id,
            amount_cents=amount_cents,
            reason=reason if reason in {"duplicate", "fraudulent", "requested_by_customer"} else "requested_by_customer",
        )

        refund = Refund(
            appointment_id=appointment_id,
            stripe_refund_id=stripe_refund_id,
            amount_cents=amount_cents,
            currency="usd",
            reason=note or reason,
            status="succeeded" if stripe_refund_id else "pending",
            created_by_user_id=actor_id,
            metadata_={"admin_initiated": True, "reason_code": reason, "note": note},
        )
        self._db.add(refund)
        await self._db.flush()

        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.PAYMENT_REFUNDED,
            entity_type="appointment",
            entity_id=str(appointment_id),
            new_value={
                "amount_cents": amount_cents,
                "stripe_refund_id": stripe_refund_id,
            },
            metadata_={
                "action": "appointment_refund",
                "reason_code": reason,
                "note": note,
                "prior_refunded": prior_refunded,
            },
        ))
        await self._db.flush()
        return refund, stripe_refund_id

    async def reassign_appointment(
        self,
        *,
        appointment_id: uuid.UUID,
        new_detailer_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str,
    ) -> tuple[uuid.UUID | None, uuid.UUID, str] | None:
        """Swap the detailer on an appointment. Returns
        (previous_detailer_id, new_detailer_id, new_status) or None if
        the appointment doesn't exist. Raises ValueError on FSM /
        business-rule violations."""
        appt = (await self._db.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if appt is None:
            return None
        if appt.status not in self._REASSIGNABLE_STATUSES:
            raise ValueError(
                f"Cannot reassign from status='{appt.status.value}'. "
                f"Allowed: {sorted(s.value for s in self._REASSIGNABLE_STATUSES)}"
            )
        if appt.detailer_id == new_detailer_id:
            raise ValueError("New detailer is already assigned to this appointment.")

        # Validate the target is actually a detailer with an approved profile.
        new_provider = (await self._db.execute(
            select(ProviderProfile).where(
                ProviderProfile.user_id == new_detailer_id,
                ProviderProfile.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if new_provider is None:
            raise ValueError("Target user is not a detailer.")
        if new_provider.application_status != "approved":
            raise ValueError(
                f"Target detailer is not approved (application_status="
                f"'{new_provider.application_status}')."
            )

        prev = appt.detailer_id
        appt.detailer_id = new_detailer_id
        # If the appointment was orphaned (NO_DETAILER_FOUND / SEARCHING),
        # bringing it back to PENDING signals the next pipeline stage that
        # the new detailer should be offered the job.
        if appt.status in (
            AppointmentStatus.NO_DETAILER_FOUND, AppointmentStatus.SEARCHING,
        ):
            appt.status = AppointmentStatus.PENDING
        appt.updated_at = datetime.now(timezone.utc)

        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.APPOINTMENT_STATUS_CHANGED,
            entity_type="appointment",
            entity_id=str(appointment_id),
            old_value={"detailer_id": str(prev) if prev else None},
            new_value={"detailer_id": str(new_detailer_id)},
            metadata_={"action": "appointment_reassign", "reason": reason},
        ))
        await self._db.flush()
        return prev, new_detailer_id, appt.status.value

    # ── Customers + credits (Plan 24 W2-E) ────────────────────────── #

    # VIP/segment thresholds — tuned for the early dataset. Promote to
    # platform_settings (Wave 4) once we have real volume.
    _VIP_LIFETIME_APPTS = 10
    _VIP_LIFETIME_SPEND_CENTS = 100_000  # $1,000
    _ACTIVE_WINDOW_DAYS = 30
    _DORMANT_WINDOW_DAYS = 90

    @classmethod
    def _classify_segment(
        cls,
        *,
        appointments_count: int,
        last_appt_at: datetime | None,
        lifetime_spend_cents: int,
        now: datetime,
    ) -> str:
        if appointments_count == 0:
            return "new"
        if (
            appointments_count >= cls._VIP_LIFETIME_APPTS
            or lifetime_spend_cents >= cls._VIP_LIFETIME_SPEND_CENTS
        ):
            return "vip"
        if last_appt_at and (now - last_appt_at).days <= cls._ACTIVE_WINDOW_DAYS:
            return "active"
        return "dormant"

    async def list_customers(
        self,
        *,
        segment: str = "all",
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        """Customers (role=client) with per-row aggregates. Segment
        filtering is applied AFTER fetching the page; for the dashboard
        view this is fine — total counts apply to the underlying client
        population, not the post-filter set."""
        # Base query — users with the client role, oldest first
        base = (
            select(User)
            .join(UserRoleAssociation, UserRoleAssociation.user_id == User.id)
            .join(Role, Role.id == UserRoleAssociation.role_id)
            .where(
                Role.name == "client",
                User.is_deleted.is_(False),
            )
        )
        if search:
            base = base.where(User.email.ilike(f"%{search}%"))

        total = (await self._db.execute(
            select(func.count()).select_from(base.subquery())
        )).scalar_one()

        stmt = (
            base
            .order_by(User.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        users = list((await self._db.execute(stmt)).scalars().all())
        if not users:
            return [], total

        user_ids = [u.id for u in users]
        now = datetime.now(timezone.utc)

        # Per-user appointments aggregate (completed only)
        appt_stmt = (
            select(
                Appointment.client_id,
                func.count(Appointment.id).label("n"),
                func.max(Appointment.scheduled_time).label("last_appt_at"),
                func.coalesce(
                    func.sum(
                        func.coalesce(Appointment.actual_price, Appointment.estimated_price)
                    ),
                    0,
                ).label("lifetime_cents"),
            )
            .where(
                Appointment.client_id.in_(user_ids),
                Appointment.status == AppointmentStatus.COMPLETED,
            )
            .group_by(Appointment.client_id)
        )
        appt_rows = (await self._db.execute(appt_stmt)).all()
        appt_by_user = {
            r.client_id: (r.n, r.last_appt_at, r.lifetime_cents) for r in appt_rows
        }

        # Per-user active credit balance
        credit_stmt = (
            select(
                CustomerCredit.user_id,
                func.coalesce(func.sum(CustomerCredit.amount_cents), 0).label("bal"),
            )
            .where(
                CustomerCredit.user_id.in_(user_ids),
                CustomerCredit.status == "active",
            )
            .group_by(CustomerCredit.user_id)
        )
        credit_rows = (await self._db.execute(credit_stmt)).all()
        credit_by_user = {r.user_id: r.bal for r in credit_rows}

        rows: list[dict] = []
        for u in users:
            n_appts, last_appt, lifetime = appt_by_user.get(u.id, (0, None, 0))
            seg = self._classify_segment(
                appointments_count=n_appts,
                last_appt_at=last_appt,
                lifetime_spend_cents=lifetime,
                now=now,
            )
            if segment != "all" and seg != segment:
                continue
            rows.append({
                "user_id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "segment": seg,
                "appointments_count": n_appts,
                "last_appointment_at": last_appt,
                "lifetime_spend_cents": int(lifetime),
                "credit_balance_cents": int(credit_by_user.get(u.id, 0)),
                "created_at": u.created_at,
            })
        return rows, total

    async def issue_customer_credit(
        self,
        *,
        user_id: uuid.UUID,
        actor_id: uuid.UUID,
        amount_cents: int,
        reason: str,
        source: str = "admin_comp",
        expires_at: datetime | None = None,
        related_appointment_id: uuid.UUID | None = None,
    ) -> CustomerCredit | None:
        """Issue a new credit row. Returns the persisted credit, or None
        if the target user doesn't exist."""
        user = (await self._db.execute(
            select(User).where(User.id == user_id, User.is_deleted.is_(False))
        )).scalar_one_or_none()
        if user is None:
            return None

        credit = CustomerCredit(
            user_id=user_id,
            amount_cents=amount_cents,
            reason=reason,
            source=source,
            status="active",
            issued_by=actor_id,
            expires_at=expires_at,
            related_appointment_id=related_appointment_id,
        )
        self._db.add(credit)
        await self._db.flush()

        self._db.add(AuditLog(
            actor_id=actor_id,
            action=AuditAction.CUSTOMER_CREDIT_ISSUED,
            entity_type="customer_credit",
            entity_id=str(credit.id),
            new_value={
                "user_id": str(user_id),
                "amount_cents": amount_cents,
                "source": source,
            },
            metadata_={
                "action": "credit_issued",
                "reason": reason,
                "related_appointment_id": str(related_appointment_id) if related_appointment_id else None,
            },
        ))
        await self._db.flush()
        return credit

    # ── Payments ──────────────────────────────────────────────────── #

    async def list_ledger_entries(
        self,
        page: int = 1,
        per_page: int = 20,
        entry_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[PaymentLedger], int]:
        base = select(PaymentLedger)
        if entry_type:
            base = base.where(PaymentLedger.entry_type == entry_type)
        if start_date:
            base = base.where(PaymentLedger.created_at >= start_date)
        if end_date:
            base = base.where(PaymentLedger.created_at <= end_date)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(PaymentLedger.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_payment_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        base_filter = []
        if start_date:
            base_filter.append(PaymentLedger.created_at >= start_date)
        if end_date:
            base_filter.append(PaymentLedger.created_at <= end_date)

        async def _sum(entry_type: str) -> int:
            stmt = select(func.coalesce(func.sum(PaymentLedger.amount_cents), 0)).where(
                PaymentLedger.entry_type == entry_type, *base_filter
            )
            return (await self._db.execute(stmt)).scalar_one()

        captured = await _sum("CAPTURE")
        refunded = await _sum("REFUND")
        commissions = await _sum("CHARGE_COMMISSION")
        payouts = await _sum("PAYOUT")

        return {
            "total_captured": captured,
            "total_refunded": refunded,
            "total_commissions": commissions,
            "total_payouts": payouts,
            "net_revenue": captured - refunded - payouts,
            "period_start": start_date,
            "period_end": end_date,
        }

    # ── Audit Log ─────────────────────────────────────────────────── #

    async def list_audit_logs(
        self,
        page: int = 1,
        per_page: int = 50,
        action: str | None = None,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[dict], int]:
        from sqlalchemy import and_, func, select
        from sqlalchemy.orm import aliased

        filters = []
        if action:
            filters.append(AuditLog.action == action)
        if actor_id:
            filters.append(AuditLog.actor_id == actor_id)
        if entity_type:
            filters.append(AuditLog.entity_type == entity_type)
        if start_date:
            filters.append(AuditLog.created_at >= start_date)
        if end_date:
            filters.append(AuditLog.created_at <= end_date)

        base = select(AuditLog).where(*filters) if filters else select(AuditLog)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._db.execute(count_stmt)).scalar_one()

        stmt = (
            base
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        logs = list((await self._db.execute(stmt)).scalars().all())

        # Fetch actor emails in a second query to avoid join complexity
        actor_ids = {log.actor_id for log in logs if log.actor_id}
        actor_emails: dict[uuid.UUID, str] = {}
        if actor_ids:
            users_stmt = select(User.id, User.email).where(User.id.in_(actor_ids))
            for uid, email in (await self._db.execute(users_stmt)).all():
                actor_emails[uid] = email

        return [
            {
                "id": log.id,
                "actor_id": log.actor_id,
                "actor_email": actor_emails.get(log.actor_id) if log.actor_id else None,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            }
            for log in logs
        ], total

    # ── Stats ──────────────────────────────────────────────────────── #

    async def get_stats(self) -> dict:
        from domains.auth.models import Role as RoleModel
        from domains.users.models import User as UserModel

        total_users = (await self._db.execute(
            select(func.count(UserModel.id)).where(UserModel.is_deleted.is_(False))
        )).scalar_one()

        active_users = (await self._db.execute(
            select(func.count(UserModel.id)).where(
                UserModel.is_deleted.is_(False), UserModel.is_active.is_(True)
            )
        )).scalar_one()

        total_detailers = (await self._db.execute(
            select(func.count(UserModel.id))
            .join(UserRoleAssociation, UserRoleAssociation.user_id == UserModel.id)
            .join(RoleModel, RoleModel.id == UserRoleAssociation.role_id)
            .where(RoleModel.name == "detailer", UserModel.is_deleted.is_(False))
        )).scalar_one()

        total_clients = (await self._db.execute(
            select(func.count(UserModel.id))
            .join(UserRoleAssociation, UserRoleAssociation.user_id == UserModel.id)
            .join(RoleModel, RoleModel.id == UserRoleAssociation.role_id)
            .where(RoleModel.name == "client", UserModel.is_deleted.is_(False))
        )).scalar_one()

        # Providers pending verification
        try:
            from domains.providers.models import ProviderProfile
            pending_verification = (await self._db.execute(
                select(func.count(ProviderProfile.id)).where(
                    ProviderProfile.verification_status == "not_submitted"
                )
            )).scalar_one()
        except Exception:
            pending_verification = 0

        # Total appointments
        try:
            from domains.appointments.models import Appointment
            total_appointments = (await self._db.execute(
                select(func.count(Appointment.id))
            )).scalar_one()
        except Exception:
            total_appointments = 0

        total_roles = (await self._db.execute(
            select(func.count(RoleModel.id)).where(RoleModel.is_deleted.is_(False))
        )).scalar_one()

        total_permissions = (await self._db.execute(
            select(func.count(Permission.id))
        )).scalar_one()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_detailers": total_detailers,
            "total_clients": total_clients,
            "pending_verification": pending_verification,
            "total_appointments": total_appointments,
            "total_roles": total_roles,
            "total_permissions": total_permissions,
        }

    # ── Ops Dashboard (Plan 24 W2-A) ───────────────────────────────── #

    _ACTIVE_STATUSES: tuple[AppointmentStatus, ...] = (
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.ARRIVED,
        AppointmentStatus.IN_PROGRESS,
    )
    _CANCELLED_STATUSES: tuple[AppointmentStatus, ...] = (
        AppointmentStatus.CANCELLED_BY_CLIENT,
        AppointmentStatus.CANCELLED_BY_DETAILER,
    )

    async def get_ops_dashboard(
        self,
        period_start: datetime,
        period_end: datetime,
        city: str = "all",
    ) -> dict:
        """Aggregate KPIs + heatmap + cities rollup for the ops dashboard.

        Bookings are bucketed by the detailer's `home_city_code` as a
        proxy until appointments carry an explicit city tag (see Plan 24
        §5.3 — A-2). When `city != 'all'`, KPIs scope to that city.
        """
        appt_filter = [
            Appointment.is_deleted.is_(False),
            Appointment.scheduled_time >= period_start,
            Appointment.scheduled_time <= period_end,
        ]
        if city != "all":
            appt_filter.append(ProviderProfile.home_city_code == city)

        appt_query_base = (
            select(Appointment)
            .outerjoin(
                ProviderProfile,
                ProviderProfile.user_id == Appointment.detailer_id,
            )
            .where(*appt_filter)
        )

        # KPI 1 — GMV (sum of actual_price on COMPLETED appointments).
        gmv_stmt = (
            select(func.coalesce(func.sum(Appointment.actual_price), 0))
            .select_from(Appointment)
            .outerjoin(
                ProviderProfile,
                ProviderProfile.user_id == Appointment.detailer_id,
            )
            .where(
                *appt_filter,
                Appointment.status == AppointmentStatus.COMPLETED,
            )
        )
        gmv_cents = (await self._db.execute(gmv_stmt)).scalar_one() or 0

        # KPI 2 — bookings count (any non-cancelled appointment).
        bookings_stmt = (
            select(func.count(Appointment.id))
            .select_from(Appointment)
            .outerjoin(
                ProviderProfile,
                ProviderProfile.user_id == Appointment.detailer_id,
            )
            .where(*appt_filter)
        )
        bookings = (await self._db.execute(bookings_stmt)).scalar_one() or 0

        # KPI 3 — active jobs right now (CONFIRMED/ARRIVED/IN_PROGRESS,
        # scoped by city when filtered). NOT bounded by the window —
        # "active right now" is a point-in-time count.
        active_filter = [
            Appointment.is_deleted.is_(False),
            Appointment.status.in_(self._ACTIVE_STATUSES),
        ]
        if city != "all":
            active_filter.append(ProviderProfile.home_city_code == city)
        active_jobs_stmt = (
            select(func.count(Appointment.id))
            .select_from(Appointment)
            .outerjoin(
                ProviderProfile,
                ProviderProfile.user_id == Appointment.detailer_id,
            )
            .where(*active_filter)
        )
        active_jobs = (await self._db.execute(active_jobs_stmt)).scalar_one() or 0

        # KPI 4 — take rate: platform commissions / GMV. Falls back to 0
        # if there's no GMV in the window.
        commissions_stmt = (
            select(func.coalesce(func.sum(PaymentLedger.amount_cents), 0))
            .where(
                PaymentLedger.entry_type == "CHARGE_COMMISSION",
                PaymentLedger.created_at >= period_start,
                PaymentLedger.created_at <= period_end,
            )
        )
        commissions_cents = (await self._db.execute(commissions_stmt)).scalar_one() or 0
        take_rate = (commissions_cents / gmv_cents * 100.0) if gmv_cents > 0 else 0.0

        # KPI 5 — CSAT (avg review rating, last 30d regardless of window
        # because review volume is too low otherwise).
        csat_window_start = period_end - timedelta(days=30)
        csat_stmt = (
            select(func.coalesce(func.avg(Review.rating), 0))
            .where(
                Review.is_deleted.is_(False),
                Review.created_at >= csat_window_start,
                Review.created_at <= period_end,
            )
        )
        csat = float((await self._db.execute(csat_stmt)).scalar_one() or 0)

        # KPI 6 — cancel rate (cancellations / total in window).
        cancelled_filter = list(appt_filter) + [
            Appointment.status.in_(self._CANCELLED_STATUSES),
        ]
        cancelled_stmt = (
            select(func.count(Appointment.id))
            .select_from(Appointment)
            .outerjoin(
                ProviderProfile,
                ProviderProfile.user_id == Appointment.detailer_id,
            )
            .where(*cancelled_filter)
        )
        cancelled = (await self._db.execute(cancelled_stmt)).scalar_one() or 0
        cancel_rate = (cancelled / bookings * 100.0) if bookings > 0 else 0.0

        # Heatmap — 7-day × 16-hour grid (hours 7..22) of booking counts,
        # normalised to a 0..5 quantile level. Uses scheduled_time in
        # UTC for V1; per-city timezone bucketing is a Wave 4 refinement.
        #
        # Why the explicit `AT TIME ZONE 'UTC'` cast: `extract(hour, ...)`
        # on a `timestamp with time zone` column uses the Postgres
        # SESSION timezone, which can differ between environments (EDT
        # in dev, UTC in CI). Casting locks the bucketing to UTC so the
        # API is deterministic regardless of where it runs.
        utc_scheduled = func.timezone("UTC", Appointment.scheduled_time)
        dow_expr = func.extract("dow", utc_scheduled)
        hour_expr = func.extract("hour", utc_scheduled)
        heat_stmt = (
            select(
                dow_expr.label("dow"),
                hour_expr.label("hour"),
                func.count(Appointment.id).label("n"),
            )
            .select_from(Appointment)
            .outerjoin(
                ProviderProfile,
                ProviderProfile.user_id == Appointment.detailer_id,
            )
            .where(*appt_filter)
            .group_by("dow", "hour")
        )
        heat_rows = (await self._db.execute(heat_stmt)).all()

        # Cities rollup — one row per non-deleted city.
        cities_stmt = (
            select(City)
            .where(City.is_deleted.is_(False))
            .order_by(City.sort_order, City.name)
        )
        cities_orm = (await self._db.execute(cities_stmt)).scalars().all()

        # Per-city detailer + active-job counts (single query, grouped).
        per_city_detailers_stmt = (
            select(
                ProviderProfile.home_city_code,
                func.count(ProviderProfile.id),
            )
            .where(
                ProviderProfile.home_city_code.is_not(None),
                ProviderProfile.application_status == "approved",
            )
            .group_by(ProviderProfile.home_city_code)
        )
        per_city_detailers: dict[str, int] = {
            code: n
            for code, n in (await self._db.execute(per_city_detailers_stmt)).all()
        }

        per_city_jobs_stmt = (
            select(
                ProviderProfile.home_city_code,
                func.count(Appointment.id),
            )
            .select_from(Appointment)
            .join(
                ProviderProfile,
                ProviderProfile.user_id == Appointment.detailer_id,
            )
            .where(
                Appointment.is_deleted.is_(False),
                Appointment.status.in_(self._ACTIVE_STATUSES),
                ProviderProfile.home_city_code.is_not(None),
            )
            .group_by(ProviderProfile.home_city_code)
        )
        per_city_jobs: dict[str, int] = {
            code: n
            for code, n in (await self._db.execute(per_city_jobs_stmt)).all()
        }

        # `online` approximation: distinct detailers with an in-flight
        # appointment right now, per city. We don't track presence yet;
        # this is the cheapest proxy.
        per_city_online_stmt = (
            select(
                ProviderProfile.home_city_code,
                func.count(func.distinct(Appointment.detailer_id)),
            )
            .select_from(Appointment)
            .join(
                ProviderProfile,
                ProviderProfile.user_id == Appointment.detailer_id,
            )
            .where(
                Appointment.is_deleted.is_(False),
                Appointment.status.in_(self._ACTIVE_STATUSES),
                ProviderProfile.home_city_code.is_not(None),
            )
            .group_by(ProviderProfile.home_city_code)
        )
        per_city_online: dict[str, int] = {
            code: n
            for code, n in (await self._db.execute(per_city_online_stmt)).all()
        }

        return {
            "gmv_cents": int(gmv_cents),
            "bookings": int(bookings),
            "active_jobs": int(active_jobs),
            "take_rate": round(float(take_rate), 2),
            "csat": round(float(csat), 2),
            "cancel_rate": round(float(cancel_rate), 2),
            "heat_rows": [
                {"dow": int(r.dow), "hour": int(r.hour), "n": int(r.n)}
                for r in heat_rows
            ],
            "cities": [
                {
                    "code": c.code,
                    "name": c.name,
                    "state": c.state,
                    "status": c.status,
                    "sort_order": c.sort_order,
                }
                for c in cities_orm
            ],
            "per_city_detailers": per_city_detailers,
            "per_city_jobs": per_city_jobs,
            "per_city_online": per_city_online,
        }
