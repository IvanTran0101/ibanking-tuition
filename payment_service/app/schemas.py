from enum import Enum
from pydantic import BaseModel, Field

class PaymentStatus(str,Enum):
    PROCESSING = "PROCESSING"
    AUTHORIZED = "AUTHORIZED"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"
    FAILED = "FAILED"
    
class PaymentInitRequest(BaseModel):
    tuition_id: str
    amount: int
    term_no: int | None = None
    user_id: str | None = None
    student_id: str

class PaymentInitResponse(BaseModel):
    payment_id: str
    status: PaymentStatus

class PaymentDTO(BaseModel):
    payment_id: str
    tuition_id: str
    user_id: str
    amount: int
    status: PaymentStatus
    expires_at: str | None = None
    complete_at: str | None = None
    
class PaymentStatusResponse(BaseModel):
    ok: bool
    payment: PaymentDTO | None = None
    error_code: str | None = None
    error_message: str | None = None
