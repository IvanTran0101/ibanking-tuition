from fastapi import APIRouter, HTTPException, status, Header

from otp_service.app.cache import get_otp, del_otp
from otp_service.app.settings import settings
from otp_service.app.messaging.publisher import publish_otp_succeed
from otp_service.app.schemas import VerifyOTPRequest


router = APIRouter()


@router.post("/otp/verify")
def verify_otp(body: VerifyOTPRequest, x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> dict:
    # Gateway should have verified JWT and injected X-User-Id
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user context")

    rec = get_otp(body.payment_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found or expired")

    # Compare code; UI handles rate limiting, no attempt tracking here
    if str(rec.get("otp")) != str(body.otp_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    # Success: clear cache and notify
    del_otp(body.payment_id)
    publish_otp_succeed(
        payment_id=body.payment_id,
        user_id=rec.get("user_id"),
        tuition_id=rec.get("tuition_id"),
        amount=rec.get("amount"),
        email=rec.get("email"),
    )
    return {"ok": True}


