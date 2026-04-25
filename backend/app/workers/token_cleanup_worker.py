# app/workers/token_cleanup_worker.py
#
# Background worker that periodically deletes expired refresh tokens.
#
# WHY: refresh_tokens accumulates rows indefinitely as tokens expire.
#      Without cleanup the table grows unboundedly, slowing index scans
#      (even with ix_refresh_tokens_expires_at) and wasting storage.
#
# INTERVAL: 24 hours — tokens expire after 7 days, so daily cleanup
#           is sufficient. Grace period of 1 day prevents deleting
#           tokens that are technically expired but still in-flight.

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_INTERVAL_SECONDS = 24 * 60 * 60   # 24 hours
_GRACE_DAYS       = 1               # delete tokens expired more than N days ago


async def token_cleanup_worker(app_state) -> None:
    """
    Runs every 24 hours. Hard-deletes refresh tokens that expired more than
    GRACE_DAYS ago. Also cleans up consumed/revoked password reset tokens.
    """
    from app.db.session import AsyncSessionLocal
    from app.repositories.refresh_token_repository import RefreshTokenRepository
    from app.repositories.password_reset_token_repository import PasswordResetTokenRepository

    logger.info("token_cleanup_worker started — interval=%dh grace=%dd",
                _INTERVAL_SECONDS // 3600, _GRACE_DAYS)

    while True:
        await asyncio.sleep(_INTERVAL_SECONDS)
        try:
            async with AsyncSessionLocal() as db:
                rt_repo  = RefreshTokenRepository(db)
                prt_repo = PasswordResetTokenRepository(db)

                rt_deleted  = await rt_repo.delete_expired(grace_period_days=_GRACE_DAYS)
                prt_deleted = await prt_repo.cleanup_expired()

                await db.commit()
                logger.info(
                    "token_cleanup: deleted %d expired refresh token(s), "
                    "%d expired password reset token(s)",
                    rt_deleted, prt_deleted,
                )
        except asyncio.CancelledError:
            logger.info("token_cleanup_worker shutting down.")
            return
        except Exception:
            logger.exception("token_cleanup_worker error — will retry in %dh",
                             _INTERVAL_SECONDS // 3600)
