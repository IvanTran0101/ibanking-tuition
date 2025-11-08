from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict

from libs.rmq import bus as rmq_bus
from sqlalchemy import text

from payment_service.app.cache import get_intent, update_intent, del_intent
from payment_service.app.db import session_scope
from payment_service.app.messaging.publisher import (
    publish_payment_authorized,
    publish_payment_completed,
    publish_payment_canceled,
    publish_payment_unauthorized,
    publish_payment_processing,
)
from payment_service.app.settings import settings

logger = logging.getLogger(__name__)


def _try_finalize(payment_id: str, correlation_id: str | None = None) -> None:
    intent = get_intent(payment_id)
    if not intent:
        return
    if not (intent.get("account_done") and intent.get("tuition_done")):
        return
    logger.info("payment_service finalizing payment_id=%s (account_done=%s tuition_done=%s)", payment_id, intent.get("account_done"), intent.get("tuition_done"))

    # Insert completed payment into DB and clear intent
    with session_scope() as db:
        db.execute(
            text(
                """
                INSERT INTO payments (payment_id, tuition_id, user_id, amount, expires_at, complete_at, status)
                VALUES (:pid, :tid, :uid, :amt, to_timestamp(:exp), :comp, :st)
                ON CONFLICT (payment_id) DO NOTHING
                """
            ),
            {
                "pid": payment_id,
                "tid": intent.get("tuition_id"),
                "uid": intent.get("user_id"),
                "amt": intent.get("amount"),
                "exp": int(intent.get("expires_at", dt.datetime.utcnow().timestamp())),
                "comp": dt.datetime.utcnow(),
                "st": "COMPLETED",
            },
        )

    del_intent(payment_id)
    publish_payment_completed(
        payment_id=payment_id,
        user_id=intent.get("user_id"),
        tuition_id=intent.get("tuition_id"),
        amount=intent.get("amount"),
        email=intent.get("email"),
        student_id=intent.get("student_id"),
        correlation_id=correlation_id,
    )
    logger.info("payment_service published payment_completed payment_id=%s", payment_id)


def on_otp_succeed(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    user_id = payload.get("user_id")
    tuition_id = payload.get("tuition_id")
    amount = payload.get("amount")
    if not (payment_id and user_id and tuition_id and amount is not None):
        return

    intent = update_intent(payment_id, {"status": "AUTHORIZED"})
    intent = get_intent(payment_id) or {}
    # Publish payment_authorized to trigger account/tuition updates
    publish_payment_authorized(
        payment_id=payment_id,
        user_id=user_id,
        tuition_id=tuition_id,
        amount=amount,
        email=intent.get("email"),
        student_id=intent.get("student_id"),
        correlation_id=(headers or {}).get("correlation-id"),
    )
    logger.info("payment_service processed OTP success payment_id=%s", payment_id)


def on_otp_expired(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    user_id = payload.get("user_id")
    tuition_id = payload.get("tuition_id")
    amount = payload.get("amount")
    if not payment_id:
        return
    # Mark unauthorized and emit event for downstream to release/unlock
    intent_snapshot = get_intent(payment_id) or {}
    update_intent(payment_id, {"status": "UNAUTHORIZED"})
    publish_payment_unauthorized(
        payment_id=payment_id,
        user_id=user_id or "",
        tuition_id=tuition_id or intent_snapshot.get("tuition_id"),
        amount=amount or intent_snapshot.get("amount"),
        email=intent_snapshot.get("email"),
        student_id=intent_snapshot.get("student_id"),
        correlation_id=(headers or {}).get("correlation-id"),
    )
    logger.warning("payment_service OTP expired payment_id=%s", payment_id)


def on_balance_updated(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    if not payment_id:
        return
    patch: Dict[str, Any] = {"account_done": True}
    email = payload.get("email")
    if isinstance(email, str) and "@" in email:
        patch["email"] = email
    intent = update_intent(payment_id, patch)
    logger.info("payment_service received balance_updated payment_id=%s", payment_id)
    _try_finalize(payment_id, correlation_id=(headers or {}).get("correlation-id"))


def on_tuition_updated(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    if not payment_id:
        return
    intent = update_intent(payment_id, {"tuition_done": True})
    logger.info("payment_service received tuition_updated payment_id=%s", payment_id)
    _try_finalize(payment_id, correlation_id=(headers or {}).get("correlation-id"))


def _try_finalize_cancel(payment_id: str, correlation_id: str | None = None) -> None:
    intent = get_intent(payment_id)
    if not intent:
        return
    # finalize cancel when both unlock + release are observed
    if not (intent.get("unlock_done") and intent.get("release_done")):
        return
    publish_payment_canceled(
        payment_id=payment_id,
        user_id=intent.get("user_id", ""),
        reason_code="canceled",
        reason_message="Payment canceled",
        email=intent.get("email"),
        student_id=intent.get("student_id"),
        correlation_id=correlation_id,
    )
    del_intent(payment_id)


def on_balance_released(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    if not payment_id:
        return
    patch: Dict[str, Any] = {"release_done": True}
    email = payload.get("email")
    if isinstance(email, str) and "@" in email:
        patch["email"] = email
    update_intent(payment_id, patch)
    logger.info("payment_service received balance_released payment_id=%s", payment_id)
    _try_finalize_cancel(payment_id, correlation_id=(headers or {}).get("correlation-id"))


def on_tuition_unlocked(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    if not payment_id:
        return
    update_intent(payment_id, {"unlock_done": True})
    logger.info("payment_service received tuition_unlocked payment_id=%s", payment_id)
    _try_finalize_cancel(payment_id, correlation_id=(headers or {}).get("correlation-id"))


def _try_start_processing(payment_id: str, correlation_id: str | None = None) -> None:
    intent = get_intent(payment_id)
    if not intent:
        return
    if intent.get("processing_sent"):
        return
    if not (intent.get("account_held") and intent.get("tuition_locked")):
        return

    # Mark as processing-sent to avoid duplicate publishes
    intent = update_intent(payment_id, {"processing_sent": True}) or intent
    publish_payment_processing(
        payment_id=payment_id,
        user_id=intent.get("user_id", ""),
        tuition_id=intent.get("tuition_id", ""),
        amount=intent.get("amount", 0),
        term=intent.get("term"),
        email=intent.get("email"),
        student_id=intent.get("student_id"),
        correlation_id=correlation_id,
    )
    logger.info(
        "payment_service published payment_processing payment_id=%s account_held=%s tuition_locked=%s",
        payment_id,
        intent.get("account_held"),
        intent.get("tuition_locked"),
    )


def on_balance_held(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    if not payment_id:
        return
    patch: Dict[str, Any] = {"account_held": True}
    email = payload.get("email")
    if isinstance(email, str) and "@" in email:
        patch["email"] = email
    update_intent(payment_id, patch)
    logger.info("payment_service received balance_held payment_id=%s", payment_id)
    _try_start_processing(payment_id, correlation_id=(headers or {}).get("correlation-id"))


def on_tuition_lock(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    if not payment_id:
        return
    update_intent(payment_id, {"tuition_locked": True})
    logger.info("payment_service received tuition_lock payment_id=%s", payment_id)
    _try_start_processing(payment_id, correlation_id=(headers or {}).get("correlation-id"))


def on_balance_hold_failed(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    user_id = payload.get("user_id") or ""
    if not payment_id:
        return
    # Publish unauthorized so services can release/unlock; cancel later when both done
    intent = get_intent(payment_id) or {}
    update_intent(payment_id, {"status": "UNAUTHORIZED"})
    logger.warning("payment_service balance_hold_failed payment_id=%s reason=%s", payment_id, payload.get("reason_code"))
    publish_payment_unauthorized(
        payment_id=payment_id,
        user_id=user_id,
        tuition_id=payload.get("tuition_id"),
        amount=payload.get("amount"),
        email=intent.get("email"),
        student_id=intent.get("student_id"),
        correlation_id=(headers or {}).get("correlation-id"),
    )
    


def on_tuition_lock_failed(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    payment_id = payload.get("payment_id")
    user_id = payload.get("user_id") or ""
    if not payment_id:
        return
    # Publish unauthorized so services can release/unlock; cancel later when both done
    intent = get_intent(payment_id) or {}
    update_intent(payment_id, {"status": "UNAUTHORIZED"})
    logger.warning("payment_service tuition_lock_failed payment_id=%s reason=%s", payment_id, payload.get("reason_code"))
    publish_payment_unauthorized(
        payment_id=payment_id,
        user_id=user_id,
        tuition_id=payload.get("tuition_id"),
        amount=payload.get("amount"),
        email=intent.get("email"),
        student_id=intent.get("student_id"),
        correlation_id=(headers or {}).get("correlation-id"),
    )
    


_EVENT_HANDLERS = {
    "otp_succeed": on_otp_succeed,
    "otp_expired": on_otp_expired,
    "balance_updated": on_balance_updated,
    "tuition_updated": on_tuition_updated,
    "balance_released": on_balance_released,
    "tuition_unlocked": on_tuition_unlocked,
    "balance_held": on_balance_held,
    "tuition_locked": on_tuition_lock,
    "balance_hold_failed": on_balance_hold_failed,
    "tuition_lock_failed": on_tuition_lock_failed,
}


def _on_message(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    event_type = (headers or {}).get("event-type") or ""
    handler = _EVENT_HANDLERS.get(event_type)
    if not handler:
        logger.debug("payment_service skipping unknown event_type=%s message_id=%s", event_type, message_id)
        return
    handler(payload, headers, message_id)


def start_consumers() -> None:
    # One queue for all payment events; dispatch based on event-type header
    rmq_bus.declare_queue(
        settings.PAYMENT_PAYMENT_QUEUE,
        settings.RK_OTP_SUCCEED,
        dead_letter=True,
        prefetch=settings.CONSUMER_PREFETCH,
    )
    ch = rmq_bus._Rmq.channel()
    # Bind other events to the same queue
    ch.queue_bind(queue=settings.PAYMENT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_OTP_EXPIRED)
    ch.queue_bind(queue=settings.PAYMENT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_BALANCE_UPDATED)
    ch.queue_bind(queue=settings.PAYMENT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_TUITION_UPDATED)
    ch.queue_bind(queue=settings.PAYMENT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_BALANCE_RELEASED)
    ch.queue_bind(queue=settings.PAYMENT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_TUITION_UNLOCKED)
    ch.queue_bind(queue=settings.PAYMENT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_BALANCE_HELD)
    ch.queue_bind(queue=settings.PAYMENT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_TUITION_LOCK)
    # Bind failure events as well
    ch.queue_bind(queue=settings.PAYMENT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_BALANCE_HOLD_FAILED)
    ch.queue_bind(queue=settings.PAYMENT_PAYMENT_QUEUE, exchange=settings.EVENT_EXCHANGE, routing_key=settings.RK_TUITION_LOCK_FAILED)

    rmq_bus.start_consume(settings.PAYMENT_PAYMENT_QUEUE, _on_message)
