from __future__ import annotations

from typing import Optional

from libs.rmq.publisher import publish_event
from otp_service.app.settings import settings


def publish_otp_generated(
    *,
    payment_id: str,
    user_id: str,
    account_id: Optional[str] = None,
    tuition_id: Optional[str] = None,
    phone_number: str,
    expires_at: str,
    correlation_id: Optional[str] = None
) -> None:
    """
    Published when OTP is generated and sent to user.
    Note: Never include the actual OTP code in the event for security!
    """
    publish_event(
        routing_key=settings.RK_OTP_GENERATED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "account_id": account_id,
            "tuition_id": tuition_id,
            "phone_number": phone_number,
            "expires_at": expires_at,
        },
        event_type="otp_generated",
        correlation_id=correlation_id,
    )


def publish_otp_expired(
    *,
    payment_id: str,
    user_id: str,
    reason_message: str,
    correlation_id: Optional[str] = None
) -> None:
    """
    Published when OTP expires without successful verification.
    """
    publish_event(
        routing_key=settings.RK_OTP_EXPIRED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "reason_message": reason_message,
        },
        event_type="otp_expired",
        correlation_id=correlation_id,
    )


def publish_otp_verified(
    *,
    payment_id: str,
    user_id: str,
    verified_at: str,
    correlation_id: Optional[str] = None
) -> None:
    """
    Published when OTP is successfully verified.
    This allows other services (like payment service) to proceed.
    """
    publish_event(
        routing_key=settings.RK_OTP_VERIFIED,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "verified_at": verified_at,
            "status": "verified"
        },
        event_type="otp_verified",
        correlation_id=correlation_id,
    )


__all__ = [
    "publish_otp_generated",
    "publish_otp_expired",
    "publish_otp_verified",
]