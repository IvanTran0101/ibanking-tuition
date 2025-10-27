from pydantic import BaseModel, Field
import uuid, datetime as dt

#otp_generated
class OTPGenerated(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "otp_generated"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.isoformat())
    payment_id: str
    user_id: str    
    tuition_id: str
    amount: int
    student_id: str | None = None
    term: str | None = None

#otp_succeed
class OTPSucceed(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "otp_succeed"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.isoformat())
    payment_id: str
    user_id: str    
    tuition_id: str
    amount: int
    student_id: str | None = None
    term: str | None = None