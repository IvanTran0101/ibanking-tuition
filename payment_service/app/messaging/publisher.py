from __future__ import annotations

from typing import Optional

from libs.rmq.publisher import publish_event
from payment_service.app.settings import settings


def publish_payment_initiated(
    *,
    payment_id: str,
    user_id: str,
    tuition_id: str,
    amount: int,
    term: int | None = None,
    email: str | None = None,
    student_id: str | None = None,
    correlation_id: Optional[str] = None,
) -> None:
    publish_event(
        routing_key=settings.RK_PAYMENT_INITIATED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "tuition_id": tuition_id,
            "amount": amount,
            "term": term,
            "email": email,
            "student_id": student_id,
        },
        event_type="payment_initiated",
        correlation_id=correlation_id,
    )


def publish_payment_processing(
    *,
    payment_id: str,
    user_id: str,
    tuition_id: str,
    amount: int,
    term: int | None = None,
    email: str | None = None,
    student_id: str | None = None,
    correlation_id: Optional[str] = None,
) -> None:
    publish_event(
        routing_key=settings.RK_PAYMENT_PROCESSING,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "tuition_id": tuition_id,
            "amount": amount,
            "term": term,
            "email": email,
            "student_id": student_id,
        },
        event_type="payment_processing",
        correlation_id=correlation_id,
    )


def publish_payment_authorized(
    *,
    payment_id: str,
    user_id: str,
    tuition_id: str,
    amount: int,
    email: str | None = None,
    student_id: str | None = None,
    correlation_id: Optional[str] = None,
) -> None:
    publish_event(
        routing_key=settings.RK_PAYMENT_AUTHORIZED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "tuition_id": tuition_id,
            "amount": amount,
            "email": email,
            "student_id": student_id,
        },
        event_type="payment_authorized",
        correlation_id=correlation_id,
    )


def publish_payment_canceled(
    *,
    payment_id: str,
    user_id: str,
    reason_code: str,
    reason_message: str,
    email: str | None = None,
    student_id: str | None = None,
    correlation_id: Optional[str] = None,
) -> None:
    # Optional; only use if you decide to propagate cancellations
    publish_event(
        routing_key=settings.RK_PAYMENT_CANCELED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "reason_code": reason_code,
            "reason_message": reason_message,
            "email": email,
            "student_id": student_id,
        },
        event_type="payment_canceled",
        correlation_id=correlation_id,
    )


def publish_payment_completed(
    *,
    payment_id: str,
    user_id: str,
    tuition_id: str,
    amount: int,
    email: str | None = None,
    student_id: str | None = None,
    correlation_id: Optional[str] = None,
) -> None:
    publish_event(
        routing_key=settings.RK_PAYMENT_COMPLETED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "tuition_id": tuition_id,
            "amount": amount,
            "email": email,
            "student_id": student_id,
        },
        event_type="payment_completed",
        correlation_id=correlation_id,
    )


__all__ = [
    "publish_payment_initiated",
    "publish_payment_processing",
    "publish_payment_authorized",
    "publish_payment_canceled",
    "publish_payment_completed",
]

def publish_payment_unauthorized(
    *,
    payment_id: str,
    user_id: str,
    tuition_id: str | None = None,
    amount: int | None = None,
    email: str | None = None,
    student_id: str | None = None,
    correlation_id: Optional[str] = None,
) -> None:
    publish_event(
        routing_key=settings.RK_PAYMENT_UNAUTHORIZED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "tuition_id": tuition_id,
            "amount": amount,
            "email": email,
            "student_id": student_id,
        },
        event_type="payment_unauthorized",
        correlation_id=correlation_id,
    )
