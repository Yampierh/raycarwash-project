"""
infrastructure/redis/client.py

Redis connection pool with fakeredis fallback for dev environments.
"""
from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import Request

logger = logging.getLogger(__name__)


async def init_redis_pool(url: str) -> aioredis.Redis:
    """Connect to Redis. Falls back to in-process fakeredis when Redis is not reachable."""
    client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    try:
        await client.ping()
        logger.info("Redis pool initialized (real Redis at %s)", url)
        return client
    except Exception:
        logger.warning(
            "Real Redis not reachable at %s — falling back to fakeredis (dev mode). "
            "Start Redis via: docker compose up -d",
            url,
        )
        await client.aclose()
        import fakeredis
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
        logger.info("Redis pool initialized (fakeredis in-process)")
        return fake


async def close_redis_pool(client: aioredis.Redis) -> None:
    await client.aclose()


async def get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis
