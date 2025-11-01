from pydantic import BaseModel
from typing import Optional


class VerifyOTPRequest(BaseModel):
    otp_code: str
    payment_id: str


class OTPVerifiedData(BaseModel):
    payment_id: str
    user_id: str
    account_id: str | None = None
    tuition_id: str | None = None
    status: str 


class VerifyOTPResponse(BaseModel):
    success: bool
    message: str | None = None
    data: OTPVerifiedData | None = None


class OTPErrorDetail(BaseModel):
    code: str
    message: str


class VerifyOTPErrorResponse(BaseModel):
    success: bool
    error: OTPErrorDetail
