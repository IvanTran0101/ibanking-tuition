from pydantic import BaseModel, Field
import uuid, datetime as dt

#balance_held
class BalanceHeld(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "balance_held"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.isoformat())
    user_id: str    
    amount: int
    payment_id: str 

#balanced_updated
class BalanceUpdated(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "balance_updated"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.isoformat())
    user_id: str    
    amount: int
    payment_id: str

#balance_hold_failed
class BalanceHoldFailed(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "balance_hold_failed"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.isoformat())
    user_id: str   
    amount: int
    reason_code: str | None = None 
    reason_message: str | None = None

#balance_released
class BalanceReleased(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "balance_released"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.isoformat())
    user_id: str   
    amount: int
    reason_code: str | None = None 
    reason_message: str | None = None