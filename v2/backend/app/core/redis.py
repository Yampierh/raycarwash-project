from __future__ import annotations

import logging
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Request

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Single connection pool shared for the lifetime of the process.
# Initialized in main.py lifespan; closed on shutdown.
_pool: aioredis.ConnectionPool | None = None


def create_redis_pool() -> aioredis.ConnectionPool:
    return aioredis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=True,
    )


def get_redis_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = create_redis_pool()
    return _pool


async def close_redis_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("Redis pool closed.")


def get_redis_client() -> aioredis.Redis:
    """Return a Redis client backed by the shared connection pool."""
    return aioredis.Redis(connection_pool=get_redis_pool())


# ------------------------------------------------------------------ #
#  FastAPI dependency                                                 #
# ------------------------------------------------------------------ #

async def get_redis(request: Request) -> aioredis.Redis:
    """
    FastAPI dependency — yields the Redis client stored on app.state.

    Usage:
        redis: aioredis.Redis = Depends(get_redis)
    """
    return request.app.state.redis
