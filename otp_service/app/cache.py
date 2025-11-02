from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any, Dict, Optional

import redis

from otp_service.app.settings import settings


@lru_cache()
def _redis() -> redis.Redis:
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=settings.REDIS_POOL_SIZE,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )


def _key(payment_id: str) -> str:
    return f"otp:{payment_id}"


def set_otp(payment_id: str, data: Dict[str, Any], ttl_sec: int) -> None:
    expires_at = int(time.time()) + int(ttl_sec)
    record = dict(data)
    record["expires_at"] = expires_at
    _redis().setex(_key(payment_id), ttl_sec, json.dumps(record))


def get_otp(payment_id: str) -> Optional[Dict[str, Any]]:
    raw = _redis().get(_key(payment_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def del_otp(payment_id: str) -> None:
    _redis().delete(_key(payment_id))


# No attempt counting; UI handles rate limiting/throttling.
