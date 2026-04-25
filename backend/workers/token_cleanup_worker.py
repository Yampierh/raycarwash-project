from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_INTERVAL_SECONDS = 24 * 60 * 60
_GRACE_DAYS       = 1


async def token_cleanup_worker(app_state) -> None:
    from infrastructure.db.session import AsyncSessionLocal
    from domains.auth.refresh_token_repository import RefreshTokenRepository
    from domains.auth.password_reset_token_repository import PasswordResetTokenRepository

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
