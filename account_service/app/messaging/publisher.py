from __future__ import annotations

import logging
from typing import Optional

from libs.rmq.publisher import publish_event
from account_service.app.settings import settings

logger = logging.getLogger(__name__)


def publish_balance_held(*, user_id: str, amount: float, payment_id: str, email: str, correlation_id: Optional[str] = None) -> None:
    publish_event(
        routing_key=settings.RK_BALANCE_HELD,
        payload={"user_id": user_id, "amount": amount, "payment_id": payment_id, "email": email},
        event_type="balance_held",
        correlation_id=correlation_id,
    )
    logger.info("event balance_held published payment_id=%s user_id=%s amount=%s", payment_id, user_id, amount)


def publish_balance_hold_failed(
    *,
    user_id: str,
    amount: float,
    payment_id: str,
    reason_code: str,
    reason_message: str,
    correlation_id: Optional[str] = None,
    email: str = "",
) -> None:
    publish_event(
        routing_key=settings.RK_BALANCE_HOLD_FAILED,
        payload={
            "user_id": user_id,
            "amount": amount,
            "payment_id": payment_id,
            "reason_code": reason_code,
            "reason_message": reason_message,
            "email": email,
        },
        event_type="balance_hold_failed",
        correlation_id=correlation_id,
    )
    logger.warning("event balance_hold_failed payment_id=%s user_id=%s reason=%s", payment_id, user_id, reason_code)


def publish_balance_updated(*, user_id: str, amount: float, payment_id: str, email: str, correlation_id: Optional[str] = None) -> None:
    publish_event(
        routing_key=settings.RK_BALANCE_UPDATED,
        payload={"user_id": user_id, "amount": amount, "payment_id": payment_id, "email": email},
        event_type="balance_updated",
        correlation_id=correlation_id,
    )
    logger.info("event balance_updated payment_id=%s user_id=%s", payment_id, user_id)


def publish_balance_released(
    *, user_id: str, amount: float, payment_id: str, reason_code: str, reason_message: str, email: str, correlation_id: Optional[str] = None
) -> None:
    publish_event(
        routing_key=settings.RK_BALANCE_RELEASED,
        payload={
            "user_id": user_id,
            "amount": amount,
            "payment_id": payment_id,
            "reason_code": reason_code,
            "reason_message": reason_message,
            "email": email,
        },
        event_type="balance_released",
        correlation_id=correlation_id,
    )
    logger.info("event balance_released payment_id=%s user_id=%s reason=%s", payment_id, user_id, reason_code)


__all__ = [
    "publish_balance_held",
    "publish_balance_hold_failed",
    "publish_balance_updated",
    "publish_balance_released",
]
