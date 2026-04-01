import logging
import os
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

_redis: Optional[redis.Redis] = None


def redis_url() -> Optional[str]:
    return os.getenv("REDIS_URL") or None


async def get_redis() -> Optional[redis.Redis]:
    global _redis
    url = redis_url()
    if not url:
        logger.info("REDIS_URL не задан — кэш отключён")
        return None
    if _redis is None:
        _redis = redis.from_url(url, decode_responses=True)
        await _redis.ping()
        logger.info("Подключение к Redis установлено")
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis отключён")
