from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, Optional

import redis

from account_service.app.settings import settings


HOLD_KEY = "hold:{payment_id}"
TOTAL_KEY = "hold-total:{user_id}"


@lru_cache()
def _redis() -> redis.Redis:
    return redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=getattr(settings, "REDIS_POOL_SIZE", 10),
    )


def _hold_key(payment_id: str) -> str:
    return HOLD_KEY.format(payment_id=payment_id)


def _total_key(user_id: str) -> str:
    return TOTAL_KEY.format(user_id=user_id)


def get_hold(payment_id: str) -> Optional[Dict[str, Any]]:
    raw = _redis().get(_hold_key(payment_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def get_total_held(user_id: str) -> float:
    raw = _redis().get(_total_key(user_id))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def create_hold(
    *,
    payment_id: str,
    user_id: str,
    amount: float,
    email: str,
    expires_at,
    ttl_seconds: int,
) -> None:
    payload = {
        "payment_id": payment_id,
        "user_id": user_id,
        "amount": amount,
        "status": "HELD",
        "email": email,
        "expires_at": expires_at.isoformat(),
    }
    r = _redis()
    total_key = _total_key(user_id)
    current_ttl = r.ttl(total_key)
    pipe = r.pipeline()
    pipe.setex(_hold_key(payment_id), ttl_seconds, json.dumps(payload))
    pipe.incrbyfloat(total_key, amount)
    if current_ttl is None or current_ttl < ttl_seconds or current_ttl < 0:
        pipe.expire(total_key, ttl_seconds)
    pipe.execute()


def remove_hold(payment_id: str) -> Optional[Dict[str, Any]]:
    key = _hold_key(payment_id)
    r = _redis()
    pipe = r.pipeline()
    pipe.get(key)
    pipe.delete(key)
    value, _ = pipe.execute()
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def decrease_total(user_id: str, amount: float) -> None:
    r = _redis()
    total_key = _total_key(user_id)
    pipe = r.pipeline()
    pipe.incrbyfloat(total_key, -amount)
    pipe.execute()
