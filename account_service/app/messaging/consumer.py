from __future__ import annotations

import datetime as dt
import uuid
import logging
from typing import Dict, Any

from sqlalchemy import text
from account_service.app.redis import holds as redis_holds

from libs.rmq import consumer as rmq_consumer
from libs.rmq import bus as rmq_bus
from libs.rmq.publisher import publish_event
from account_service.app.messaging.publisher import (
    publish_balance_held,
    publish_balance_hold_failed,
    publish_balance_updated,
    publish_balance_released,
)
from account_service.app.db import session_scope
from account_service.app.settings import settings

logger = logging.getLogger(__name__)


def _on_message(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    event_type = (headers or {}).get("event-type") or ""
    if event_type == "payment_initiated":
        logger.info("account_service received payment_initiated payment_id=%s user_id=%s", payload.get("payment_id"), payload.get("user_id"))
        _handle_payment_initiated(payload, headers, message_id)
    elif event_type == "payment_authorized":
        logger.info("account_service received payment_authorized payment_id=%s user_id=%s", payload.get("payment_id"), payload.get("user_id"))
        _handle_payment_authorized(payload, headers, message_id)
    elif event_type == "payment_unauthorized":
        logger.info("account_service received payment_unauthorized payment_id=%s", payload.get("payment_id"))
        _handle_payment_unauthorized(payload, headers, message_id)
    else:
        # Unknown event: ignore idempotently
        return


def _handle_payment_initiated(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    user_id = payload.get("user_id")
    amount = payload.get("amount")
    payment_id = payload.get("payment_id")
    if not (user_id and amount and payment_id):
        return

    with session_scope() as db:
        # Lock account row
        acc = db.execute(
            text("SELECT user_id, balance, email FROM accounts WHERE user_id = :uid FOR UPDATE"),
            {"uid": user_id},
        ).first()
        if not acc:
            logger.warning("account_service user not found user_id=%s payment_id=%s", user_id, payment_id)
            publish_balance_hold_failed(
                user_id=user_id,
                amount=amount,
                payment_id=payment_id,
                reason_code="user_not_found",
                reason_message="user_not_found",
                correlation_id=(headers or {}).get("correlation-id"),
                email="",
            )
            return

        # Idempotency: if hold already exists in redis, no-op
        if redis_holds.get_hold(payment_id):
            return

        # Available = balance - total held in redis
        total_held = redis_holds.get_total_held(user_id)
        available = float(acc.balance) - float(amount) - total_held
        if available < 0:
            logger.warning("account_service insufficient funds user_id=%s payment_id=%s available=%s required=%s", user_id, payment_id, acc.balance, amount)
            publish_balance_hold_failed(
                user_id=user_id,
                amount=amount,
                payment_id=payment_id,
                reason_code="insufficient_funds",
                reason_message="insufficient_funds",
                correlation_id=(headers or {}).get("correlation-id"),
                email=str(getattr(acc, "email", "")),
            )
            return

        # Create hold in Redis
        expires_at = dt.datetime.utcnow() + dt.timedelta(minutes=settings.HOLD_EXPIRES_MIN)
        redis_holds.create_hold(
            payment_id=payment_id,
            user_id=user_id,
            amount=float(amount),
            email=str(getattr(acc, "email", "")),
            expires_at=expires_at,
            ttl_seconds=settings.HOLD_EXPIRES_MIN * 60,
        )

    publish_balance_held(
        user_id=user_id,
        amount=amount,
        payment_id=payment_id,
        email=str(getattr(acc, "email", "")),
        correlation_id=(headers or {}).get("correlation-id"),
    )
    logger.info("account_service placed hold user_id=%s payment_id=%s amount=%s", user_id, payment_id, amount)


def _handle_payment_authorized(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    user_id = payload.get("user_id")
    amount = payload.get("amount")
    payment_id = payload.get("payment_id")
    if not (user_id and amount and payment_id):
        return

    hold = redis_holds.remove_hold(payment_id)
    if not hold:
        return

    with session_scope() as db:
        db.execute(
            text("UPDATE accounts SET balance = balance - :amt WHERE user_id = :uid"),
            {"amt": amount, "uid": user_id},
        )
    redis_holds.decrease_total(user_id, float(amount))

    if True:
        # lookup email for user
        email: str = ""
        with session_scope() as db:
            row = db.execute(text("SELECT email FROM accounts WHERE user_id=:uid"), {"uid": user_id}).first()
            if row:
                try:
                    email = str(row[0])
                except Exception:
                    email = ""
        publish_balance_updated(
            user_id=user_id,
            amount=amount,
            payment_id=payment_id,
            email=email,
            correlation_id=(headers or {}).get("correlation-id"),
        )
        logger.info("account_service captured hold user_id=%s payment_id=%s", user_id, payment_id)


def _handle_payment_unauthorized(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    """
    Release a previously HELD balance when the payment is unauthorized/expired.
    Does not modify account balance; transitions hold to RELEASED and publishes balance_released.
    """
    payment_id = payload.get("payment_id")
    reason_code = payload.get("reason_code", "unauthorized")
    reason_message = payload.get("reason_message", "Payment unauthorized or OTP expired")
    if not payment_id:
        return

    hold = redis_holds.remove_hold(payment_id)
    to_publish: Dict[str, Any] | None = None
    if hold and hold.get("status") == "HELD":
        redis_holds.decrease_total(hold["user_id"], float(hold["amount"]))
        to_publish = {
            "user_id": hold["user_id"],
            "amount": float(hold["amount"]),
        }

    if to_publish:
        # lookup email for user
        email: str = ""
        with session_scope() as db:
            row = db.execute(text("SELECT email FROM accounts WHERE user_id=:uid"), {"uid": str(to_publish["user_id"]) }).first()
            if row:
                try:
                    email = str(row[0])
                except Exception:
                    email = ""
        publish_balance_released(
            user_id=str(to_publish["user_id"]),
            amount=float(to_publish["amount"]),
            payment_id=str(payment_id),
            reason_code=reason_code,
            reason_message=reason_message,
            email=email,
            correlation_id=(headers or {}).get("correlation-id"),
        )
        logger.info("account_service released hold user_id=%s payment_id=%s reason=%s", to_publish["user_id"], payment_id, reason_code)



def start_consumers() -> None:
    # Declare a single queue and bind both routing keys
    rmq_bus.declare_queue(settings.ACCOUNT_PAYMENT_QUEUE, settings.RK_PAYMENT_INITIATED, dead_letter=True, prefetch=settings.CONSUMER_PREFETCH)
    # Bind second key manually
    ch = rmq_bus._Rmq.channel()
    ch.queue_bind(queue=settings.ACCOUNT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_PAYMENT_AUTHORIZED)
    ch.queue_bind(queue=settings.ACCOUNT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_PAYMENT_UNAUTHORIZED)
    # Start consuming on one thread
    rmq_bus.start_consume(settings.ACCOUNT_PAYMENT_QUEUE, _on_message)
