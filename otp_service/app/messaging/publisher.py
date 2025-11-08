from __future__ import annotations

import logging
from typing import Optional

from libs.rmq.publisher import publish_event
from otp_service.app.settings import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def publish_otp_generated(
    *,
    payment_id: str,
    user_id: str,
    tuition_id: Optional[str],
    amount: int,
    otp: str,
    email: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    publish_event(
        routing_key=settings.RK_OTP_GENERATED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "tuition_id": tuition_id,
            "amount": amount,
            "otp": otp,
            "email": email,
        },
        event_type="otp_generated",
        correlation_id=correlation_id,
    )
    logger.info("otp_service published otp_generated payment_id=%s user_id=%s", payment_id, user_id)


def publish_otp_succeed(*, payment_id: str, user_id: str, tuition_id: Optional[str], amount: int, email: Optional[str] = None, correlation_id: Optional[str] = None) -> None:
    publish_event(
        routing_key=settings.RK_OTP_SUCCEED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "tuition_id": tuition_id,
            "amount": amount,
            "email": email,
        },
        event_type="otp_succeed",
        correlation_id=correlation_id,
    )
    logger.info("otp_service published otp_succeed payment_id=%s user_id=%s", payment_id, user_id)


def publish_otp_expired(*, payment_id: str, user_id: str, tuition_id: Optional[str], amount: int, reason_code: str, reason_message: str, email: Optional[str] = None, correlation_id: Optional[str] = None) -> None:
    publish_event(
        routing_key=settings.RK_OTP_EXPIRED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "tuition_id": tuition_id,
            "amount": amount,
            "reason_code": reason_code,
            "reason_message": reason_message,
            "email": email,
        },
        event_type="otp_expired",
        correlation_id=correlation_id,
    )
    logger.info(
        "otp_service published otp_expired payment_id=%s user_id=%s reason=%s",
        payment_id,
        user_id,
        reason_code,
    )


__all__ = [
    "publish_otp_generated",
    "publish_otp_succeed",
    "publish_otp_expired",
]
