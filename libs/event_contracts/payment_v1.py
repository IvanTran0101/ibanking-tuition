from pydantic import BaseModel, Field
import uuid, datetime as dt

#payment_initiated
class PaymentInitiated(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "payment_initiated"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    payment_id: str
    user_id: str    
    tuition_id: str
    amount: int
    student_id: str | None = None
    term: str | None = None

#payment_processing
class PaymentProcessing(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "payment_processing"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    payment_id: str
    user_id: str    
    tuition_id: str
    amount: int
    student_id: str | None = None
    term: str | None = None

#payment_authorized
class PaymentAuthorized(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "payment_authorized"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    payment_id: str
    user_id: str  
    tuition_id: str  
    amount: int
    student_id: str | None = None
    term: str | None = None

#payment_completed
class PaymentCompleted(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "payment_completed"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    payment_id: str
    user_id: str  
    tuition_id: str  
    amount: int
    student_id: str | None = None
    term: str | None = None

#payment_completed
class PaymentUnauthorized(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "payment_unauthorized"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    payment_id: str
    user_id: str   
    amount: int
    student_id: str | None = None
    term: str | None = None
    reason_code: str | None = None 
    reason_message: str | None = None

#payment_canceled
class PaymentCanceled(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "payment_canceled"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    payment_id: str
    user_id: str  
    amount: int
    student_id: str | None = None
    term: str | None = None
    reason_code: str | None = None 
    reason_message: str | None = None
