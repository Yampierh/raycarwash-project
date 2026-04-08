# app/db/session.py
#
# WHY this file exists (Sprint 2 refactor):
# In Sprint 1, the engine lived in app/models/models.py. That worked when
# main.py was the only consumer. Now that app/services/auth.py needs to
# import `get_db`, and auth.py is also imported by main.py, a circular
# import chain forms:
#
#   main → auth → models (for User) → main (for get_db)  ← 💥
#
# The fix is the standard FastAPI/SQLAlchemy pattern: isolate all session
# infrastructure in its own module that has NO imports from the rest of the app.
# Both models AND services can import from here without creating a cycle.

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# ------------------------------------------------------------------ #
#  Engine                                                             #
# ------------------------------------------------------------------ #
# One engine per process. asyncpg maintains an internal connection pool
# within the engine — we tune it here once and share it everywhere.

engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DEBUG,   # SQL logging — DEBUG only, never in production
    future=True,           # Enforce SQLAlchemy 2.0 behaviour globally
)

# ------------------------------------------------------------------ #
#  Session factory                                                    #
# ------------------------------------------------------------------ #
# expire_on_commit=False prevents SQLAlchemy from expiring all ORM
# attributes after `session.commit()`. In a synchronous context that
# would trigger a lazy load to refresh them. In an async context it
# raises MissingGreenlet. We keep attributes alive for the full request.

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ------------------------------------------------------------------ #
#  FastAPI dependency: get_db                                         #
# ------------------------------------------------------------------ #
# Why a generator dependency instead of a plain context manager?
# FastAPI's Depends() system calls `next()` to enter the generator and
# then calls `close()` (or `throw()` on exception) after the response
# is sent — guaranteeing cleanup even if an unhandled exception occurs
# mid-handler. This pattern gives us request-scoped sessions for free.

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a request-scoped async database session.

    - On success:  commits the transaction, then closes the session.
    - On failure:  rolls back the transaction, then re-raises the exception
                   (so FastAPI's exception handlers can still respond correctly).

    Injected via:  db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise