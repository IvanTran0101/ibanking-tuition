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

    # Student id is a plain code now (e.g., 523K0017)
    # Be tolerant to extra spaces/casing from UI input
    sid = (student_id or "").strip()

    # 1) Pick the earliest unpaid term (amount_due > 0)
    first_unpaid_sql = text(
        """
        SELECT 
            t.tuition_id::text   AS tuition_id,
            t.student_id::text   AS student_id,
            t.student_full_name  AS full_name,
            t.term_no            AS term_no,
            t.amount_due::float8 AS amount_due,
            t.status::text       AS status
        FROM tuitions t
        WHERE t.student_id = :sid
          AND t.status = 'UNLOCKED'
        ORDER BY t.term_no ASC
        LIMIT 1
        """
    )
    row = db.execute(first_unpaid_sql, {"sid": sid}).mappings().first()

    # 2) If all paid, return the latest term (highest term_no)
    if not row:
        latest_sql = text(
            """
            SELECT 
                t.tuition_id::text   AS tuition_id,
                t.student_id::text   AS student_id,
                t.student_full_name  AS full_name,
                t.term_no            AS term_no,
                t.amount_due::float8 AS amount_due,
                t.status::text       AS status
            FROM tuitions t
            WHERE t.student_id = :sid
            ORDER BY t.term_no DESC
            LIMIT 1
            """
        )
        row = db.execute(latest_sql, {"sid": sid}).mappings().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tuition record not found for student"
        )

    return {
        "ok": True,
        "tuition_id": row["tuition_id"],
        "student_id": row["student_id"],
        "term_no": int(row["term_no"]),
        "full_name": row["full_name"],
        "amount_due": row["amount_due"],
        "status": row["status"],
    }
