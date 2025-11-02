from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any, Dict, Optional

import redis

from payment_service.app.settings import settings


@lru_cache()
def _redis() -> redis.Redis:
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=settings.DB_POOL_SIZE,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )


def _key(payment_id: str) -> str:
    return f"payment:{payment_id}"


def set_intent(payment_id: str, data: Dict[str, Any], ttl_sec: int) -> None:
    expires_at = int(time.time()) + int(ttl_sec)
    record = dict(data)
    record.setdefault("status", "PROCESSING")
    record["expires_at"] = expires_at
    _redis().setex(_key(payment_id), ttl_sec, json.dumps(record))


def get_intent(payment_id: str) -> Optional[Dict[str, Any]]:
    raw = _redis().get(_key(payment_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def update_intent(payment_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    r = _redis()
    key = _key(payment_id)
    pipe = r.pipeline()
    while True:
        try:
            pipe.watch(key)
            cur = r.get(key)
            if cur is None:
                pipe.unwatch()
                return None
            cur_obj = json.loads(cur)
            cur_obj.update(patch)
            ttl = r.ttl(key)
            pipe.multi()
            pipe.setex(key, ttl if ttl and ttl > 0 else 300, json.dumps(cur_obj))
            pipe.execute()
            return cur_obj
        except redis.WatchError:
            continue
        finally:
            pipe.reset()


def del_intent(payment_id: str) -> None:
    _redis().delete(_key(payment_id))

