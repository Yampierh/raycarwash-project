"""
workers/schedule.py — RQ-scheduler cron registrations.

Run this module once when the rq-scheduler container starts. Each entry
is idempotent: if a job with the same id already exists in Redis, we
update its schedule instead of creating a duplicate.

Usage (from the rq-scheduler container):
    python -m workers.schedule
    rqscheduler --host redis --port 6379 --db 0 --verbose

TODO(phase 9): add the rest of the Profile workers as their chunks
land — achievement_evaluator, account_deletion_finalizer,
data_export_builder, document_expiry_checker,
service_reminder_dispatcher, audit_log_redactor.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from redis import Redis
from rq_scheduler import Scheduler

from app.core.config import get_settings

logger = logging.getLogger("raycarwash.workers.schedule")


_JOB_DEFS = [
    {
        "id": "pending_contact_cleanup",
        "func": "workers.pending_contact_cleanup.run",
        "cron": "0 * * * *",  # top of every hour
        "queue": "low",
    },
    {
        "id": "login_history_purger",
        "func": "workers.login_history_purger.run",
        "cron": "0 3 1 * *",  # 03:00 on the 1st of each month
        "queue": "low",
    },
    # TODO(phase 9): document_expiry_checker — cron "0 1 * * *"
    # TODO(phase 9): account_deletion_finalizer — cron "0 3 * * *"
    # TODO(phase 9): audit_log_redactor — cron "0 4 1 * *"
    # TODO(phase 9): service_reminder_dispatcher — cron "0 9 * * *"
    # TODO(phase 9): achievement_evaluator — cron "0 2 * * *"
]


def register_all() -> None:
    settings = get_settings()
    conn = Redis.from_url(settings.REDIS_URL)
    scheduler = Scheduler(connection=conn)

    # Drop our existing jobs so cron changes take effect on redeploy.
    for job in scheduler.get_jobs():
        if job.id in {d["id"] for d in _JOB_DEFS}:
            scheduler.cancel(job)

    for definition in _JOB_DEFS:
        scheduler.cron(
            definition["cron"],
            func=definition["func"],
            id=definition["id"],
            queue_name=definition["queue"],
            use_local_timezone=False,
            timeout="15m",
        )
        logger.info(
            "scheduled %s (%s) on cron %s",
            definition["id"],
            definition["func"],
            definition["cron"],
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    register_all()
    logger.info(
        "schedule.py registered %d jobs at %s",
        len(_JOB_DEFS),
        datetime.now(timezone.utc).isoformat(),
    )
