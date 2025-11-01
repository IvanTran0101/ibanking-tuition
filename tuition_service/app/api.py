from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from tuition_service.app.db import get_db
from tuition_service.app.schemas import StudentIdResponse

router = APIRouter()

@router.get("/tuition/{student_id}", response_model=StudentIdResponse)
def get_tuition(
    student_id: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db)
) -> dict:
    
    # Gateway should verify JWT and inject X-User-Id header
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user context")

    sql = text(
        """
        SELECT 
            t.tuition_id::text,
            s.student_id::text,
            t.term_no::text,
            t.amount_due::float8
            t.status::text,
        FROM tuition t
        JOIN student s ON s.student_id = t.student_id
        WHERE s.student_id = :sid
        """
    )

    row = db.execute(sql, {"sid": student_id}).mappings().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tuition record not found for student"
        )

    return {
        "ok": True,
        "tuition_id": row["tuition_id"],
        "student_id": row["student_id"],
        "term_no": row["term_no"],
        "amount_due": row["amount_due"],
        "status": row["status"],
    }
