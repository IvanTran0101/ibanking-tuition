from pydantic import BaseModel, Field
import uuid, datetime as dt

#payment_initiated
class PaymentInitiated(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "payment_initiated"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.isoformat())
    payment_id: str
    user_id: str
    amount: int
    student_id: str | None = None
    term: str | None = None
    
class PaymentProcessing(BaseModel):
    event_id: str = Field(default_factory=)