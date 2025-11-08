from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

import os
from libs.rmq import bus as rmq_bus
from notification_service.app.settings import settings
from libs.http.client import HttpClient

logger = logging.getLogger(__name__)


def _send_email(to: str, subject: str, body: str) -> None:
    """Send HTML email via SMTP"""
    if settings.DRY_RUN:
        logger.info(f"[DRY RUN] Email to {to}: {subject}")
        return
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to
        msg.attach(MIMEText(body, "html", "utf-8"))
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to, msg.as_string())
        
        logger.info(f"Email sent to {to}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise


def _on_message(payload: Dict[str, Any], headers: Dict[str, Any]) -> None:
    """Handle notification events"""
    event_type = (headers or {}).get("event-type", "")
    user_id = payload.get("user_id")
    payment_id = payload.get("payment_id")
    
    if not user_id or not payment_id:
        return
    
    email_in_payload = payload.get("email")
    user_email = email_in_payload if isinstance(email_in_payload, str) and "@" in email_in_payload else None

    if not user_email:
        try:
            base_url = os.getenv("ACCOUNT_SERVICE_URL", "http://account_service:8080")
            client = HttpClient(base_url=base_url)
            corr_id = (headers or {}).get("correlation-id")
            resp = client.get(
                "/accounts/me",
                headers={"X-User-Id": str(user_id)},
                correlation_id=corr_id,
            )
            data = resp.json()
            em = data.get("email") if isinstance(data, dict) else None
            if isinstance(em, str) and "@" in em:
                user_email = em
        except Exception as e:
            logger.warning(f"Email lookup failed for user {user_id}: {e}")

    if not user_email:
        return
    
    if event_type == "otp_generated":
        otp = payload.get("otp")
        if not otp:
            return
        _send_email(
            to=user_email,
            subject="Your OTP Code",
            body=f"""
            <h2>Your OTP Code</h2>
            <p>Your OTP code is: <strong style="font-size: 24px;">{otp}</strong></p>
            <p>Payment ID: {payment_id}</p>
            <p>This code expires in 5 minutes.</p>
            """
        )
    
    elif event_type == "payment_completed":
        amount = payload.get("amount")
        if amount is None:
            return
        _send_email(
            to=user_email,
            subject="Payment Receipt",
            body=f"""
            <h2>✅ Payment Successful</h2>
            <p>Payment ID: {payment_id}</p>
            <p>Amount: ${amount:,.2f}</p>
            <p>Thank you for your payment!</p>
            """
        )


def start_consumers() -> None:
    """Start notification consumer"""
    rmq_bus.declare_queue(
        settings.NOTIFICATION_QUEUE,
        settings.RK_OTP_GENERATED,
        dead_letter=True,
        prefetch=settings.CONSUMER_PREFETCH
    )
    
    ch = rmq_bus._Rmq.channel()
    ch.queue_bind(
        queue=settings.NOTIFICATION_QUEUE,
        exchange=settings.EVENT_EXCHANGE,
        routing_key=settings.RK_PAYMENT_COMPLETED
    )
    
    logger.info(f"Starting notification consumer on {settings.NOTIFICATION_QUEUE}")
    rmq_bus.start_consume(settings.NOTIFICATION_QUEUE, _on_message)
