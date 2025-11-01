from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import datetime as dt
import redis

from otp_service.app.schemas import (
    VerifyOTPRequest, 
    VerifyOTPResponse, 
    VerifyOTPErrorResponse,
    OTPVerifiedData,
    OTPErrorDetail
)
from otp_service.app.settings import settings
from otp_service.app.messaging.publisher import publish_otp_verified, publish_otp_expired
from otp_service.app.cache import get_redis_client


router = APIRouter()


@router.post("/otp/verify")
def verify_otp(
    req: VerifyOTPRequest,
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Verify OTP code for a payment intent.
    OTP data is stored in Redis with key format: otp:{intent_id}
    
    User only needs to provide the OTP code and intent_id.
    The user_id is retrieved from the stored OTP data.
    
    Returns 200 with success=true if verified
    Returns 404 with success=false if not found/expired
    """
    intent_id = req.intent_id
    otp_code = req.otp_code
    
    # Construct Redis keys
    otp_key = f"otp:{intent_id}"
    attempts_key = f"otp:attempts:{intent_id}"
    
    # Check if OTP exists (not expired)
    stored_data = redis_client.get(otp_key)
    if not stored_data:
        # Can't publish expired event without user_id, but that's okay
        # The OTP generation event already tracked this intent
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "OTP_NOT_FOUND",
                    "message": "OTP not found or has expired"
                }
            }
        )
    
    # Parse stored data (format: "otp_code|user_id|account_id|tuition_id|phone_number|created_at")
    try:
        parts = stored_data.decode('utf-8').split('|')
        stored_otp = parts[0]
        user_id = parts[1]  # Extract user_id from stored data
        account_id = parts[2] if len(parts) > 2 and parts[2] else None
        tuition_id = parts[3] if len(parts) > 3 and parts[3] else None
        phone_number = parts[4] if len(parts) > 4 else None
        created_at = parts[5] if len(parts) > 5 else None
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_OTP_DATA",
                    "message": "Invalid OTP data format in cache"
                }
            }
        )
    
    # Check attempts
    attempts = redis_client.get(attempts_key)
    current_attempts = int(attempts.decode('utf-8')) if attempts else 0
    
    if current_attempts >= settings.OTP_MAX_ATTEMPTS:
        # Max attempts reached, delete OTP
        redis_client.delete(otp_key)
        redis_client.delete(attempts_key)
        
        publish_otp_expired(
            payment_id=intent_id,
            user_id=user_id,
            reason_message="Maximum verification attempts exceeded"
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "MAX_ATTEMPTS_EXCEEDED",
                    "message": "Maximum verification attempts exceeded"
                }
            }
        )
    
    # Verify OTP code
    if otp_code != stored_otp:
        # Increment attempts
        new_attempts = current_attempts + 1
        redis_client.setex(attempts_key, settings.OTP_EXPIRES_SEC, str(new_attempts))
        
        attempts_remaining = settings.OTP_MAX_ATTEMPTS - new_attempts
        
        # UI handles the failure, no event published
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_OTP",
                    "message": f"Invalid OTP code. {attempts_remaining} attempt(s) remaining"
                }
            }
        )
    
    # OTP verified successfully
    # Clean up Redis keys
    redis_client.delete(otp_key)
    redis_client.delete(attempts_key)
    
    verified_at = dt.datetime.utcnow().isoformat()
    
    publish_otp_verified(
        payment_id=intent_id,
        user_id=user_id,
        verified_at=verified_at
    )
    
    # Return success response with data, including user_id
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "OTP verified successfully",
            "data": {
                "intent_id": intent_id,
                "user_id": user_id,  
                "account_id": account_id,
                "tuition_id": tuition_id,
                "status": "verified"
            }
        }
    )


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "otp-service"}