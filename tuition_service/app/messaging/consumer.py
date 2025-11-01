from __future__ import annotations

import datetime as dt
import uuid
from typing import Dict, Any

from sqlalchemy import text

from libs.rmq import consumer as rmq_consumer
from libs.rmq import bus as rmq_bus
from libs.rmq.publisher import publish_event
from tuition_service.app.messaging.publisher import (
    publish_tuition_locked,
    publish_tuition_lock_failed,
    publish_tuition_updated,
)
from tuition_service.app.db import session_scope
from tuition_service.app.settings import settings


def _on_message(payload: Dict[str, Any], headers: Dict[str, Any], message_id: str) -> None:
    event_type = (headers or {}).get("event-type") or ""
    if event_type == "payment_initiated":
        _handle_payment_initiated(payload, headers, message_id)
    elif event_type == "payment_authorized":
        _handle_payment_authorized(payload, headers, message_id)
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
        # Lock tuition record
        tuition = db.execute(
            text(
                """
                SELECT t.tuition_id, t.student_id, t.term_no, t.amount_due, t.status
                FROM tuition t
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

        # Idempotency: check if lock already exists for this payment
        existing_lock = db.execute(
            text("SELECT status FROM tuition_locks WHERE payment_id = :pid"),
            {"pid": payment_id}
        ).first()
        if existing_lock:
            return

        # Check if tuition is already paid or locked by another payment
        if tuition["status"] not in ["PENDING", "UNPAID"]:
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

        # Create lock
        expires_at = dt.datetime.utcnow() + dt.timedelta(minutes=settings.HOLD_EXPIRES_MIN)
        db.execute(
            text(
                """
                INSERT INTO tuition_locks (lock_id, tuition_id, student_id, amount, expires_at, status, payment_id)
                VALUES (:lid, :tid, :sid, :amt, :exp, 'LOCKED', :pid)
                """
            ),
            {
                "lid": str(uuid.uuid4()),
                "tid": tuition_id,
                "sid": student_id,
                "amt": amount,
                "exp": expires_at,
                "pid": payment_id,
            },
        )

        # Update tuition status to LOCKED
        db.execute(
            text("UPDATE tuition SET status = 'LOCKED' WHERE tuition_id = :tid"),
            {"tid": tuition_id}
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
        # Check lock exists and is valid
        lock = db.execute(
            text(
                """
                SELECT amount, status 
                FROM tuition_locks 
                WHERE payment_id = :pid AND tuition_id = :tid AND student_id = :sid 
                FOR UPDATE
                """
            ),
            {"pid": payment_id, "tid": tuition_id, "sid": student_id},
        ).mappings().first()
        
        if lock and lock["status"] == "LOCKED":
            # Get tuition info before updating
            tuition_data = db.execute(
                text(
                    """
                    SELECT tuition_id, student_id, term_no, amount_due, status
                    FROM tuition
                    WHERE tuition_id = :tid
                    FOR UPDATE
                    """
                ),
                {"tid": tuition_id}
            ).mappings().first()
            
            if tuition_data:
                # Update tuition status to PAID
                db.execute(
                    text("UPDATE tuition SET status = 'PAID' WHERE tuition_id = :tid"),
                    {"tid": tuition_id},
                )
                
                # Capture the lock
                db.execute(
                    text("UPDATE tuition_locks SET status = 'CAPTURED' WHERE payment_id = :pid"),
                    {"pid": payment_id},
                )
                updated = True

    if updated and tuition_data:
        publish_tuition_updated(
            student_id=student_id,
            tuition_id=tuition_id,
            term_no=tuition_data["term_no"],
            amount_due=tuition_data["amount_due"],
            status="PAID",
            payment_id=payment_id,
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
    
    # Start consuming
    rmq_bus.start_consume(settings.TUITION_PAYMENT_QUEUE, _on_message)