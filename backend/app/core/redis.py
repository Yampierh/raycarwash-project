# COMPATIBILITY SHIM — re-exports from infrastructure/redis/client.py
from infrastructure.redis.client import init_redis_pool, close_redis_pool, get_redis  # noqa: F401
