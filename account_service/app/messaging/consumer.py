from __future__ import annotations

import datetime as dt
import uuid
from typing import Dict, Any

from sqlalchemy import text

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


def _on_message(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    event_type = (headers or {}).get("event-type") or ""
    if event_type == "payment_initiated":
        _handle_payment_initiated(payload, headers, message_id)
    elif event_type == "payment_authorized":
        _handle_payment_authorized(payload, headers, message_id)
    elif event_type == "payment_unauthorized":
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

        # Idempotency: if hold already exists, no-op
        existing = db.execute(
            text("SELECT status FROM holds WHERE payment_id = :pid"), {"pid": payment_id}
        ).first()
        if existing:
            return

        # Available = balance - sum(holds HELD)
        sum_held = db.execute(
            text(
                "SELECT COALESCE(SUM(amount),0) FROM holds WHERE user_id=:uid AND status='HELD'"
            ),
            {"uid": user_id},
        ).scalar_one()
        available = float(acc.balance) - float(amount) - float(sum_held)
        if available < 0:
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

        # Create hold
        expires_at = dt.datetime.utcnow() + dt.timedelta(minutes=settings.HOLD_EXPIRES_MIN)
        db.execute(
            text(
                """
                INSERT INTO holds (hold_id, user_id, amount, expires_at, status, payment_id)
                VALUES (:hid, :uid, :amt, :exp, 'HELD', :pid)
                """
            ),
            {
                "hid": str(uuid.uuid4()),
                "uid": user_id,
                "amt": amount,
                "exp": expires_at,
                "pid": payment_id,
            },
        )

    publish_balance_held(
        user_id=user_id,
        amount=amount,
        payment_id=payment_id,
        email=str(getattr(acc, "email", "")),
        correlation_id=(headers or {}).get("correlation-id"),
    )


def _handle_payment_authorized(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    user_id = payload.get("user_id")
    amount = payload.get("amount")
    payment_id = payload.get("payment_id")
    if not (user_id and amount and payment_id):
        return

    updated = False
    with session_scope() as db:
        hold = db.execute(
            text("SELECT amount, status FROM holds WHERE payment_id=:pid AND user_id=:uid FOR UPDATE"),
            {"pid": payment_id, "uid": user_id},
        ).mappings().first()
        if hold and hold["status"] == "HELD":
            # Deduct balance and capture hold
            db.execute(
                text("UPDATE accounts SET balance = balance - :amt WHERE user_id = :uid"),
                {"amt": amount, "uid": user_id},
            )
            db.execute(
                text("UPDATE holds SET status='CAPTURED' WHERE payment_id=:pid"),
                {"pid": payment_id},
            )
            updated = True

    if updated:
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

    to_publish: Dict[str, Any] | None = None
    with session_scope() as db:
        hold = db.execute(
            text(
                "SELECT user_id, amount, status FROM holds WHERE payment_id=:pid FOR UPDATE"
            ),
            {"pid": payment_id},
        ).mappings().first()
        if hold and hold["status"] == "HELD":
            db.execute(
                text("UPDATE holds SET status='RELEASED' WHERE payment_id=:pid"),
                {"pid": payment_id},
            )
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



def start_consumers() -> None:
    # Declare a single queue and bind both routing keys
    rmq_bus.declare_queue(settings.ACCOUNT_PAYMENT_QUEUE, settings.RK_PAYMENT_INITIATED, dead_letter=True, prefetch=settings.CONSUMER_PREFETCH)
    # Bind second key manually
    ch = rmq_bus._Rmq.channel()
    ch.queue_bind(queue=settings.ACCOUNT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_PAYMENT_AUTHORIZED)
    ch.queue_bind(queue=settings.ACCOUNT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_PAYMENT_UNAUTHORIZED)
    # Start consuming on one thread
    rmq_bus.start_consume(settings.ACCOUNT_PAYMENT_QUEUE, _on_message)
