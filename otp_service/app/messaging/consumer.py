from __future__ import annotations
import logging
import random
from typing import Dict, Any

from libs.rmq.consumer import run, Subscription
from otp_service.app.messaging.publisher import (
    publish_otp_generated,
    publish_otp_succeed,
    publish_otp_expired,
)
from libs.rmq import bus as rmq_bus
from otp_service.app.cache import set_otp
from otp_service.app.settings import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def _gen_otp(length: int) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(max(4, length)))


def on_payment_processing(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id") 
    user_id = payload.get("user_id")
    tuition_id = payload.get("tuition_id")
    amount = payload.get("amount")
    email = payload.get("email")
    if not payment_id or not user_id or amount is None:
        logger.warning(
            "otp_service skipping payment_processing message_id=%s missing fields payment_id=%s user_id=%s amount=%s",
            message_id,
            payment_id,
            user_id,
            amount,
        )
        return

    logger.info(
        "otp_service received payment_processing payment_id=%s user_id=%s tuition_id=%s",
        payment_id,
        user_id,
        tuition_id,
    )

    otp_code = _gen_otp(settings.OTP_LENGTH)
    set_otp(
        payment_id,
        {"otp": otp_code, "user_id": user_id, "tuition_id": tuition_id, "amount": amount, "email": email},
        ttl_sec=settings.OTP_TTL_SEC,
    )

    publish_otp_generated(
        payment_id=payment_id,
        user_id=user_id,
        tuition_id=tuition_id,
        amount=amount,
        otp=otp_code,
        email=email,
        correlation_id=(headers or {}).get("correlation-id"),
    )
    logger.info(
        "otp_service stored OTP for payment_id=%s otp=%s ttl_sec=%s",
        payment_id,
        otp_code,
        settings.OTP_TTL_SEC,
    )


def start_consumers() -> None:
    # Ensure queue exists and bound to payment processing key
    rmq_bus.declare_queue(settings.OTP_QUEUE, settings.RK_PAYMENT_PROCESSING, dead_letter=True, prefetch=settings.CONSUMER_PREFETCH)
    subs: list[Subscription] = [Subscription(settings.OTP_QUEUE, settings.RK_PAYMENT_PROCESSING, on_payment_processing)]
    run(subs, join=False)
