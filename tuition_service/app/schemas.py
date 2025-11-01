from pydantic import BaseModel


class StudentIdResponse(BaseModel):
    ok: bool
    tuition_id: str | None = None
    student_id: str | None = None
    term_no: str | None = None
    amount_due: float | None = None
    status: str | None = None
