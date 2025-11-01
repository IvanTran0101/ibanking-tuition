from __future__ import annotations

from typing import Optional

from libs.rmq.publisher import publish_event
from tuition_service.app.settings import settings


def publish_tuition_locked(
    *,
    student_id: str,
    tuition_id: str,
    term_no: str,
    amount_due: float,
    status: str,
    payment_id: str,
    correlation_id: Optional[str] = None
) -> None:
    publish_event(
        routing_key=settings.RK_TUITION_LOCK,
        payload={
            "student_id": student_id,
            "tuition_id": tuition_id,
            "term_no": term_no,
            "amount_due": amount_due,
            "status": status,
            "payment_id": payment_id,
        },
        event_type="tuition_lock",
        correlation_id=correlation_id,
    )


def publish_tuition_lock_failed(
    *,
    student_id: str,
    tuition_id: str,
    term_no: str,
    amount_due: float,
    status: str,
    payment_id: str,
    reason_code: str,
    reason_message: str,
    correlation_id: Optional[str] = None,
) -> None:
    publish_event(
        routing_key=settings.RK_TUITION_LOCK_FAILED,
        payload={
            "student_id": student_id,
            "tuition_id": tuition_id,
            "term_no": term_no,
            "amount_due": amount_due,
            "status": status,
            "payment_id": payment_id,
            "reason_code": reason_code,
            "reason_message": reason_message,
        },
        event_type="tuition_lock_failed",
        correlation_id=correlation_id,
    )


def publish_tuition_updated(
    *,
    student_id: str,
    tuition_id: str,
    term_no: str,
    amount_due: float,
    status: str,
    payment_id: str,
    correlation_id: Optional[str] = None
) -> None:
    publish_event(
        routing_key=settings.RK_TUITION_UPDATED,
        payload={
            "student_id": student_id,
            "tuition_id": tuition_id,
            "term_no": term_no,
            "amount_due": amount_due,
            "status": status,
            "payment_id": payment_id,
        },
        event_type="tuition_updated",
        correlation_id=correlation_id,
    )


def publish_tuition_unlocked(
    *,
    student_id: str,
    tuition_id: str,
    term_no: str,
    amount_due: float,
    status: str,
    payment_id: str,
    reason_code: str,
    reason_message: str,
    correlation_id: Optional[str] = None
) -> None:
    publish_event(
        routing_key=settings.RK_TUITION_UNLOCKED,
        payload={
            "student_id": student_id,
            "tuition_id": tuition_id,
            "term_no": term_no,
            "amount_due": amount_due,
            "status": status,
            "payment_id": payment_id,
            "reason_code": reason_code,
            "reason_message": reason_message,
        },
        event_type="tuition_unlocked",
        correlation_id=correlation_id,
    )


__all__ = [
    "publish_tuition_locked",
    "publish_tuition_lock_failed",
    "publish_tuition_updated",
    "publish_tuition_unlocked",
]