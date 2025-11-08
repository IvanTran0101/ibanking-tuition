from fastapi import APIRouter, HTTPException, status, Header
import uuid, datetime as dt

from payment_service.app.settings import settings
from payment_service.app.schemas import PaymentInitRequest, PaymentInitResponse
from payment_service.app.cache import set_intent
from payment_service.app.messaging.publisher import publish_payment_initiated

router = APIRouter()

@router.post("/payments/init", response_model=PaymentInitResponse)
def init_payment(body: PaymentInitRequest, x_user_id: str | None = Header(None, alias="X-User-Id")) -> PaymentInitResponse:
    if not x_user_id or body.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")

    payment_id = str(uuid.uuid4())
    expires_at = (dt.datetime.utcnow() + dt.timedelta(minutes=15)).isoformat()

    # Save intent in Redis (stateless DB until completed)
    set_intent(payment_id, {
        "user_id": x_user_id,
        "tuition_id": body.tuition_id,
        "amount": body.amount,
        "term": body.term_no,
        "student_id": body.student_id,
        "status": "PROCESSING",
    }, ttl_sec=15*60)

    # Publish PaymentInitiated once; both Account and Tuition receive it
    publish_payment_initiated(
        payment_id=payment_id,
        user_id=x_user_id,
        tuition_id=body.tuition_id,
        amount=body.amount,
        term=body.term_no,
        student_id=body.student_id,
    )

    return PaymentInitResponse(payment_id=payment_id, status="PROCESSING")
