from pydantic import BaseModel, Field
import uuid, datetime as dt

#balance_held
class BalanceHeld(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "balance_held"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.isoformat())
    user_id: str    
    amount: int

#balanced_updated
class BalanceUpdated(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "balance_updated"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.isoformat())
    user_id: str    
    amount: int