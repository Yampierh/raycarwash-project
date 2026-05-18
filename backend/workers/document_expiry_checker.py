"""
workers/document_expiry_checker.py — nudge detailers ahead of KYC
document expiry.

Runs daily via rq-scheduler. Finds Documents with `expires_at` in the
next 30 days that haven't yet been notified, and dispatches a
"your insurance / business license expires in N days" reminder.

To keep the worker idempotent (Stripe-style at-least-once delivery
semantics for the scheduler), we track sent reminders by stamping
the audit log instead of mutating the Document. A per-document
audit entry with `action=DOCUMENT_UPLOADED, metadata.reminder_for=<id>`
would conflict with the upload audit; instead we use a synthetic
`DOCUMENT_DELETED`-adjacent shape and key off the (entity_id,
day-bucketed metadata).

Actually — the simpler design is "send at most once per (document,
threshold-bucket)" by checking whether we ALREADY emitted a notif
audit row keyed on the bucket. Buckets: 30d, 14d, 7d, 1d. Each
threshold triggers exactly one notification per document.

Notification dispatch is intentionally a logger.info today — the
real notification path (EmailAdapter + Expo Push) is plumbed in
Phase 7. The worker SHIPS the trigger; integrating the channel is
a follow-up.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, select

from domains.audit.models import AuditAction, AuditLog
from domains.users.document import Document
from infrastructure.db.session import AsyncSessionLocal

logger = logging.getLogger("raycarwash.workers.document_expiry_checker")


# Buckets are checked in order from broadest to narrowest. A doc
# expiring tomorrow has already crossed the 30d/14d/7d thresholds
# but we want to send EACH threshold's notification once — so we
# only send the bucket for which a notification hasn't already
# fired AND the current date is within the bucket window.
_THRESHOLD_DAYS = [30, 14, 7, 1]


def _bucket_for_days_remaining(days_remaining: int) -> int | None:
    """Return the threshold bucket a doc currently falls into, or
    None if outside any window.

      - 31+ days remaining → None (too early to nudge)
      - 15-30             → 30
      - 8-14              → 14
      - 2-7               → 7
      - 0-1               → 1
      - <0                → 1 (already lapsed — still bucket 1 so
                              admins see the audit trail)
    """
    if days_remaining < 0:
        return 1
    for threshold in _THRESHOLD_DAYS:
        if days_remaining <= threshold:
            # Find the SMALLEST threshold the doc satisfies — that's
            # the most urgent unsent bucket.
            pass
    # Walk smallest → largest and return the first satisfied.
    for threshold in sorted(_THRESHOLD_DAYS):
        if days_remaining <= threshold:
            return threshold
    return None


async def _has_already_notified(
    session, doc_id, bucket: int,
) -> bool:
    """Return True iff we previously logged a reminder for this
    (doc, bucket) pair."""
    stmt = (
        select(AuditLog.id)
        .where(
            AuditLog.entity_type == "document",
            AuditLog.entity_id == str(doc_id),
            AuditLog.action == AuditAction.DOCUMENT_UPLOADED,
            # metadata_ contains {"reminder_bucket": <int>} — we use
            # the metadata_ column the audit_log extension landed in
            # Phase 0 to mark synthetic reminder entries.
            AuditLog.metadata_["reminder_bucket"].astext == str(bucket),
        )
        .limit(1)
    )
    found = (await session.execute(stmt)).scalar_one_or_none()
    return found is not None


async def _check_with_session(session) -> int:
    """Inner helper — caller owns the transaction. Returns number of
    reminder notifications dispatched."""
    today = date.today()
    horizon = today + timedelta(days=max(_THRESHOLD_DAYS))

    # Pull every non-deleted doc whose expires_at is within the
    # widest threshold. The partial index `idx_documents_expiring`
    # from m_011 keeps the scan tight (most rows have NULL expires_at).
    stmt = (
        select(Document)
        .where(
            Document.is_deleted.is_(False),
            Document.expires_at.is_not(None),
            Document.expires_at <= horizon,
        )
    )
    candidates = (await session.scalars(stmt)).all()

    dispatched = 0
    for doc in candidates:
        days_remaining = (doc.expires_at - today).days
        bucket = _bucket_for_days_remaining(days_remaining)
        if bucket is None:
            continue
        if await _has_already_notified(session, doc.id, bucket):
            continue

        # Today's MVP "notification" is a structured log line. Phase 7
        # swaps this for the real channels (email + push) once the
        # NotificationDispatcher lands.
        # TODO(phase 7): replace logger.info with
        #   await NotificationDispatcher.send(
        #       user_id=doc.user_id,
        #       template="document_expiring",
        #       data={"doc_id": str(doc.id), "type": doc.type,
        #             "days_remaining": days_remaining,
        #             "expires_at": doc.expires_at.isoformat()},
        #   )
        logger.info(
            "document expiry reminder — user=%s doc=%s type=%s "
            "expires_at=%s days_remaining=%d bucket=%dd",
            doc.user_id, doc.id, doc.type,
            doc.expires_at.isoformat(),
            days_remaining, bucket,
        )

        # Audit row stamps the (doc, bucket) so we don't re-send.
        # actor_id=None because this is a system-initiated event.
        session.add(AuditLog(
            actor_id=None,
            action=AuditAction.DOCUMENT_UPLOADED,
            entity_type="document",
            entity_id=str(doc.id),
            metadata_={
                "source": "document_expiry_checker",
                "reminder_bucket": bucket,
                "days_remaining": days_remaining,
                "dispatched_at": datetime.now(timezone.utc).isoformat(),
            },
        ))
        dispatched += 1

    if dispatched:
        logger.info(
            "document_expiry_checker dispatched %d reminders", dispatched,
        )
    return dispatched


async def _run_once() -> int:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            return await _check_with_session(session)


def run() -> int:
    return asyncio.run(_run_once())
