from __future__ import annotations

import datetime as dt
import uuid
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
    
    if not (student_id and tuition_id and amount and payment_id):
        return

    with session_scope() as db:
        # Lock tuition record (row-level lock)
        tuition = db.execute(
            text(
                """
                SELECT t.tuition_id, t.student_id, t.term_no, t.amount_due, t.status
                FROM tuitions t
                WHERE t.tuition_id = :tid AND t.student_id = :sid
                FOR UPDATE
                """
            ),
            {"tid": tuition_id, "sid": student_id},
        ).mappings().first()
        
        if not tuition:
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
            publish_tuition_lock_failed(
                student_id=student_id,
                tuition_id=tuition_id,
                term_no=tuition["term_no"],
                amount_due=tuition["amount_due"],
                status=tuition["status"],
                payment_id=payment_id,
                reason_code="invalid_status",
                reason_message=f"Tuition status is {tuition['status']}, cannot lock",
                correlation_id=(headers or {}).get("correlation-id"),
            )
            return

        # Check if amount matches
        if abs(float(tuition["amount_due"]) - float(amount)) > 0.01:
            publish_tuition_lock_failed(
                student_id=student_id,
                tuition_id=tuition_id,
                term_no=tuition["term_no"],
                amount_due=tuition["amount_due"],
                status=tuition["status"],
                payment_id=payment_id,
                reason_code="amount_mismatch",
                reason_message=f"Amount mismatch: expected {tuition['amount_due']}, got {amount}",
                correlation_id=(headers or {}).get("correlation-id"),
            )
            return

        # Lock tuition on the same row and set payment_id + expires_at TTL
        expires_at = dt.datetime.utcnow() + dt.timedelta(minutes=settings.HOLD_EXPIRES_MIN)
        db.execute(
            text(
                """
                UPDATE tuitions
                SET status = 'LOCKED', payment_id = :pid, expires_at = :exp
                WHERE tuition_id = :tid AND student_id = :sid AND status = 'UNLOCKED'
                """
            ),
            {"pid": payment_id, "exp": expires_at, "tid": tuition_id, "sid": student_id},
        )

    publish_tuition_locked(
        student_id=student_id,
        tuition_id=tuition_id,
        term_no=tuition["term_no"],
        amount_due=tuition["amount_due"],
        status="LOCKED",
        payment_id=payment_id,
        correlation_id=(headers or {}).get("correlation-id"),
    )


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
    
    if not (student_id and tuition_id and amount and payment_id):
        return

    updated = False
    tuition_data = None
    
    with session_scope() as db:
        # Lock the tuition row by payment_id
        tuition_data = db.execute(
            text(
                """
                SELECT tuition_id, student_id, term_no, amount_due, status
                FROM tuitions
                WHERE payment_id = :pid AND tuition_id = :tid AND student_id = :sid
                FOR UPDATE
                """
            ),
            {"pid": payment_id, "tid": tuition_id, "sid": student_id},
        ).mappings().first()

        if tuition_data and tuition_data["status"] == "LOCKED":
            # Mark as unlocked (paid) and optionally set amount_due to 0
            db.execute(
                text(
                    "UPDATE tuitions SET status='UNLOCKED', amount_due = 0 WHERE tuition_id = :tid"
                ),
                {"tid": tuition_id},
            )
            updated = True

    if updated and tuition_data:
        publish_tuition_updated(
            student_id=student_id,
            tuition_id=tuition_id,
            term_no=tuition_data["term_no"],
            amount_due=0,
            status="UNLOCKED",
            payment_id=payment_id,
            correlation_id=(headers or {}).get("correlation-id"),
        )


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
                SELECT tuition_id, student_id, term_no, amount_due, status
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
