from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional


_lock = threading.Lock()
_store: Dict[str, Dict[str, Any]] = {}


def set_otp(payment_id: str, data: Dict[str, Any], ttl_sec: int) -> None:
    expires_at = int(time.time()) + int(ttl_sec)
    record = dict(data)
    record["expires_at"] = expires_at
    with _lock:
        _store[payment_id] = record


def get_otp(payment_id: str) -> Optional[Dict[str, Any]]:
    now = int(time.time())
    with _lock:
        rec = _store.get(payment_id)
        if not rec:
            return None
        if rec.get("expires_at", 0) < now:
            _store.pop(payment_id, None)
            return None
        return dict(rec)


def del_otp(payment_id: str) -> None:
    with _lock:
        _store.pop(payment_id, None)


# No attempt counting; UI handles rate limiting/throttling.
