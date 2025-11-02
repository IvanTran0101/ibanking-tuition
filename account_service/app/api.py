from fastapi import APIRouter, Depends, Header, HTTPException, status
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


@router.get("/accounts/me")
def get_me(x_user_id: str | None = Header(default=None, alias="X-User-Id"), db: Session = Depends(get_db)) -> dict:
    # Gateway should verify JWT and inject X-User-Id header
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing user context")

    sql = text(
        """
        SELECT user_id::text AS user_id, full_name, phone_number, balance::float8 AS balance, username, email
        FROM accounts
        WHERE user_id = :uid
        """
    )
    row = db.execute(sql, {"uid": x_user_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "ok": True,
        "user_id": row["user_id"],
        "full_name": row["full_name"],
        "phone_number": row["phone_number"],
        "balance": row["balance"],
        "username": row["username"],
        "email": row["email"],
    }
