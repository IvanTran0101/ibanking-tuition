from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from account_service.app.db import get_db
from account_service.app.schemas import VerifyRequest, VerifyResponse
from account_service.app.security import verify_password_hash


router = APIRouter()


@router.post("/internal/accounts/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest, db: Session = Depends(get_db)) -> VerifyResponse:
    sql = text(
        """
        SELECT user_id::text AS user_id, password_hash, full_name, phone_number, balance::float8 AS balance
        FROM accounts
        WHERE username = :username
        """
    )
    row = db.execute(sql, {"username": req.username}).mappings().first()
    if not row:
        return VerifyResponse(ok=False)

    if not verify_password_hash(row["password_hash"], req.password_hash):
        return VerifyResponse(ok=False)

    return VerifyResponse(
        ok=True,
        user_id=row["user_id"],
        full_name=row["full_name"],
        phone_number=row["phone_number"],
        balance=row["balance"],
    )
