from pydantic import BaseModel, Field
import uuid, datetime as dt

#tuition_locked
class TuitionLocked(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "tuition_locked"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    tuition_id: str
    amount_due: int
    student_id: str | None = None
    term: str | None = None
    payment_id: str

#tuition_updated
class TuitionUpdated(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "tuition_updated"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    payment_id: str
    tuition_id: str
    amount_due: int
    student_id: str | None = None
    term: str | None = None

#tuition_lock_failed
class TuitionLockFailed(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "tuition_lock_failed"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    payment_id: str
    tuition_id: str
    amount_due: int
    student_id: str | None = None
    term: str | None = None
    reason_code: str | None = None 
    reason_message: str | None = None

#tuition_unlocked
class TuitionUnlocked(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "tuition_unlocked"
    occurred_at: str = Field(default_factory=lambda: dt.datetime.utcnow().isoformat())
    payment_id: str
    tuition_id: str
    amount_due: int
    student_id: str | None = None
    term: str | None = None
    reason_code: str | None = None 
    reason_message: str | None = None
