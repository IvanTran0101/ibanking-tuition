from __future__ import annotations

import datetime as dt
import uuid
import logging
from typing import Dict, Any

from sqlalchemy import text

from libs.rmq import bus as rmq_bus
from tuition_service.app.messaging.publisher import (
    publish_tuition_locked,
    publish_tuition_lock_failed,
    publish_tuition_updated,
    publish_tuition_unlocked,
)
from tuition_service.app.db import session_scope
from tuition_service.app.settings import settings

logger = logging.getLogger(__name__)


def _on_message(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    event_type = (headers or {}).get("event-type") or ""
    if event_type == "payment_initiated":
        logger.info("tuition_service received payment_initiated payment_id=%s tuition_id=%s", payload.get("payment_id"), payload.get("tuition_id"))
        _handle_payment_initiated(payload, headers, message_id)
    elif event_type == "payment_authorized":
        logger.info("tuition_service received payment_authorized payment_id=%s tuition_id=%s", payload.get("payment_id"), payload.get("tuition_id"))
        _handle_payment_authorized(payload, headers, message_id)
    elif event_type == "payment_unauthorized":
        logger.info("tuition_service received payment_unauthorized payment_id=%s", payload.get("payment_id"))
        _handle_payment_unauthorized(payload, headers, message_id)
    else:
        # Unknown event: ignore idempotently
        return


def _handle_payment_initiated(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    """
    Lock the tuition record when payment is initiated.
    Unlike account service which checks balance, here we:
    1. Verify the tuition record exists and is unpaid
    2. Lock it to prevent duplicate payments
    """
    student_id = payload.get("student_id")  # Different from user_id in account service
    tuition_id = payload.get("tuition_id")
    amount = payload.get("amount")
    payment_id = payload.get("payment_id")
    
    logger.info(
        "tuition_service payment_initiated raw payload student_id=%s tuition_id=%s amount=%s payment_id=%s",
        student_id,
        tuition_id,
        amount,
        payment_id,
    )

    if not (tuition_id and amount and payment_id):
        logger.warning(
            "tuition_service missing required fields (tuition_id=%s amount=%s payment_id=%s); skipping lock",
            tuition_id,
            amount,
            payment_id,
        )
        return

    with session_scope() as db:
        # Lock tuition record (row-level lock)
        params = {"tid": tuition_id}
        query = """
                SELECT 
                    t.tuition_id::text AS tuition_id,
                    t.student_id,
                    t.term_no,
                    t.amount_due,
                    t.status
                FROM tuitions t
                WHERE t.tuition_id = :tid
        """
        if student_id:
            query += " AND t.student_id = :sid"
            params["sid"] = student_id
        query += " FOR UPDATE"
        tuition = db.execute(text(query), params).mappings().first()
        
        if not tuition:
            logger.warning("tuition_service tuition_not_found tuition_id=%s student_id=%s payment_id=%s", tuition_id, student_id, payment_id)
            publish_tuition_lock_failed(
                student_id=student_id,
                tuition_id=tuition_id,
                term_no="",
                amount_due=amount,
                status="NOT_FOUND",
                payment_id=payment_id,
                reason_code="tuition_not_found",
                reason_message="Tuition record not found",
                correlation_id=(headers or {}).get("correlation-id"),
            )
            return

        # Check if tuition is already locked or not in UNLOCKED state
        if tuition["status"] != "UNLOCKED":
            logger.warning("tuition_service invalid_status tuition_id=%s status=%s", tuition_id, tuition["status"])
            publish_tuition_lock_failed(
                student_id=student_id,
                tuition_id=tuition_id,
                term_no=tuition["term_no"],
                amount_due=float(tuition["amount_due"]),
                status=tuition["status"],
                payment_id=payment_id,
                reason_code="invalid_status",
                reason_message=f"Tuition status is {tuition['status']}, cannot lock",
                correlation_id=(headers or {}).get("correlation-id"),
            )
            return

        # Check if amount matches
        if abs(float(tuition["amount_due"]) - float(amount)) > 0.01:
            logger.warning("tuition_service amount_mismatch tuition_id=%s expected=%s actual=%s", tuition_id, tuition["amount_due"], amount)
            publish_tuition_lock_failed(
                student_id=student_id,
                tuition_id=tuition_id,
                term_no=tuition["term_no"],
                amount_due=float(tuition["amount_due"]),
                status=tuition["status"],
                payment_id=payment_id,
                reason_code="amount_mismatch",
                reason_message=f"Amount mismatch: expected {tuition['amount_due']}, got {amount}",
                correlation_id=(headers or {}).get("correlation-id"),
            )
            return

        # ensure student_id populated from DB
        student_id = student_id or tuition["student_id"]

        # Lock tuition on the same row and set payment_id + expires_at TTL
        expires_at = dt.datetime.utcnow() + dt.timedelta(minutes=settings.HOLD_EXPIRES_MIN)
        locked_row = db.execute(
            text(
                """
                UPDATE tuitions
                SET status = 'LOCKED', payment_id = :pid, expires_at = :exp
                WHERE tuition_id = :tid AND student_id = :sid AND status = 'UNLOCKED'
                RETURNING 
                    tuition_id::text AS tuition_id, 
                    student_id, 
                    term_no, 
                    amount_due, 
                    status
                """
            ),
            {"pid": payment_id, "exp": expires_at, "tid": tuition_id, "sid": student_id},
        ).mappings().first()

    if not locked_row:
        logger.warning("tuition_service lock_race tuition_id=%s payment_id=%s", tuition_id, payment_id)
        publish_tuition_lock_failed(
            student_id=student_id,
            tuition_id=tuition_id,
            term_no=tuition["term_no"],
            amount_due=float(tuition["amount_due"]),
            status=tuition["status"],
            payment_id=payment_id,
            reason_code="lock_race",
            reason_message="Tuition lock could not be captured (possibly already locked).",
            correlation_id=(headers or {}).get("correlation-id"),
        )
        return

    publish_tuition_locked(
        student_id=locked_row["student_id"],
        tuition_id=str(locked_row["tuition_id"]),
        term_no=locked_row["term_no"],
        amount_due=float(locked_row["amount_due"]),
        status=locked_row["status"],
        payment_id=payment_id,
        correlation_id=(headers or {}).get("correlation-id"),
    )
    logger.info("tuition_service locked tuition_id=%s payment_id=%s", tuition_id, payment_id)


def _handle_payment_authorized(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    """
    Mark tuition as paid when payment is authorized.
    Unlike account service which deducts balance, here we:
    1. Update tuition status to PAID
    2. Capture the lock
    """
    student_id = payload.get("student_id")
    tuition_id = payload.get("tuition_id")
    amount = payload.get("amount")
    payment_id = payload.get("payment_id")
    
    logger.info(
        "tuition_service payment_authorized raw payload student_id=%s tuition_id=%s amount=%s payment_id=%s",
        student_id,
        tuition_id,
        amount,
        payment_id,
    )

    if not (tuition_id and payment_id):
        logger.warning(
            "tuition_service missing fields for payment_authorized (tuition_id=%s payment_id=%s); skipping capture",
            tuition_id,
            payment_id,
        )
        return

    updated = False
    tuition_data = None
    
    with session_scope() as db:
        # Lock the tuition row by payment_id
        tuition_data = db.execute(
            text(
                """
                SELECT 
                    tuition_id::text AS tuition_id, 
                    student_id, 
                    term_no, 
                    amount_due, 
                    status
                FROM tuitions
                WHERE payment_id = :pid AND tuition_id = :tid
                FOR UPDATE
                """
            ),
            {"pid": payment_id, "tid": tuition_id},
        ).mappings().first()

        if tuition_data and tuition_data["status"] == "LOCKED":
            # Mark tuition as PAID; keep original amount_due for reporting
            db.execute(
                text(
                    "UPDATE tuitions SET status='PAID', expires_at = NULL WHERE tuition_id = :tid AND student_id = :sid"
                ),
                {"tid": tuition_id, "sid": tuition_data["student_id"]},
            )
            updated = True

    if updated and tuition_data:
        student_id = student_id or tuition_data["student_id"]
        publish_tuition_updated(
            student_id=student_id,
            tuition_id=tuition_id,
            term_no=tuition_data["term_no"],
            amount_due=float(tuition_data["amount_due"]),
            status="PAID",
            payment_id=payment_id,
            correlation_id=(headers or {}).get("correlation-id"),
        )
        logger.info("tuition_service marked tuition paid tuition_id=%s payment_id=%s", tuition_id, payment_id)


def _handle_payment_unauthorized(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    """
    When a payment is unauthorized/expired, release the tuition lock.
    1. Find the tuition row locked by payment_id
    2. Set status back to UNLOCKED and clear lock fields
    3. Publish tuition_unlocked for downstream
    """
    payment_id = payload.get("payment_id")
    reason_code = payload.get("reason_code", "unauthorized")
    reason_message = payload.get("reason_message", "Payment unauthorized or OTP expired")
    if not payment_id:
        return

    tuition_data = None
    with session_scope() as db:
        tuition_data = db.execute(
            text(
                """
                SELECT 
                    tuition_id::text AS tuition_id, 
                    student_id, 
                    term_no, 
                    amount_due, 
                    status
                FROM tuitions
                WHERE payment_id = :pid
                FOR UPDATE
                """
            ),
            {"pid": payment_id},
        ).mappings().first()

        if tuition_data and tuition_data["status"] == "LOCKED":
            db.execute(
                text(
                    """
                    UPDATE tuitions
                    SET status = 'UNLOCKED', payment_id = NULL, expires_at = NULL
                    WHERE tuition_id = :tid AND student_id = :sid AND status = 'LOCKED'
                    """
                ),
                {"tid": tuition_data["tuition_id"], "sid": tuition_data["student_id"]},
            )

    if tuition_data:
        publish_tuition_unlocked(
            student_id=tuition_data["student_id"],
            tuition_id=tuition_data["tuition_id"],
            term_no=tuition_data["term_no"],
            amount_due=float(tuition_data["amount_due"]),
            status="UNLOCKED",
            payment_id=payment_id,
            reason_code=reason_code,
            reason_message=reason_message,
            correlation_id=(headers or {}).get("correlation-id"),
        )
        logger.info("tuition_service released tuition lock tuition_id=%s payment_id=%s reason=%s", tuition_data["tuition_id"], payment_id, reason_code)
    else:
        logger.warning("tuition_service could not find locked tuition for payment_id=%s during unauthorized flow", payment_id)


def start_consumers() -> None:
    # Declare queue and bind both routing keys
    rmq_bus.declare_queue(
        settings.TUITION_PAYMENT_QUEUE, 
        settings.RK_PAYMENT_INITIATED, 
        dead_letter=True, 
        prefetch=settings.CONSUMER_PREFETCH
    )
    
    # Bind second key manually
    ch = rmq_bus._Rmq.channel()
    ch.queue_bind(
        queue=settings.TUITION_PAYMENT_QUEUE, 
        exchange=settings.EVENT_EXCHANGE, 
        routing_key=settings.RK_PAYMENT_AUTHORIZED
    )
    ch.queue_bind(
        queue=settings.TUITION_PAYMENT_QUEUE,
        exchange=settings.EVENT_EXCHANGE,
        routing_key=settings.RK_PAYMENT_UNAUTHORIZED,
    )
    
    # Start consuming
    rmq_bus.start_consume(settings.TUITION_PAYMENT_QUEUE, _on_message)
