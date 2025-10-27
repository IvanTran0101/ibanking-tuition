
# libs/rmq/publisher.py
import time
from typing import Dict, Any, Optional
from .bus import publish

def publish_event(routing_key: str,
                  payload: Dict[str, Any],
                  *,
                  event_type: str,
                  event_version: str = "v1",
                  idempotency_key: Optional[str] = None,
                  correlation_id: Optional[str] = None) -> None:
    """
    Chuẩn hoá header cho mọi event.
    """
    headers = {
        "event-type": event_type,
        "event-version": event_version,
        "occurred-at": int(time.time() * 1000),
    }
    if idempotency_key:
        headers["idempotency-key"] = idempotency_key
    if correlation_id:
        headers["correlation-id"] = correlation_id

    publish(routing_key=routing_key, body=payload, headers=headers)
