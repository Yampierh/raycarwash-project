from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import Request

logger = logging.getLogger(__name__)


async def init_redis_pool(url: str) -> aioredis.Redis:
    """
    Try to connect to the real Redis at `url`.
    Falls back to an in-process fakeredis instance in dev when Redis
    is not running — no config change required.
    """
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


async def close_redis_pool(redis: aioredis.Redis) -> None:
    await redis.aclose()


async def get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis
