from __future__ import annotations

import redis
from functools import lru_cache

from otp_service.app.settings import settings


@lru_cache()
def get_redis_client() -> redis.Redis:
    """
    Create and return Redis client.
    Uses lru_cache to ensure single instance.
    decode_responses=False because we manually decode to handle missing keys gracefully.
    """
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=False,  # Manual decode for better control
        max_connections=settings.REDIS_POOL_SIZE,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True
    )