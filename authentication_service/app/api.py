from fastapi import APIRouter, HTTPException, status

from authentication_service.app.schemas import LoginRequest, LoginResponse
from authentication_service.app.security.jwt import create_access_token, hash_password
from authentication_service.app.settings import settings
from authentication_service.app.clients.account_client import AccountClient


router = APIRouter()


@router.post("/authentication/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    # Hash password before sending to account service
    pwd_hash = hash_password(body.password, settings.PASSWORD_SALT)

    client = AccountClient()
    result = client.verify_credentials(body.username, pwd_hash)

    if not result.get("ok"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_id = result.get("user_id")
    token = create_access_token(subject=str(user_id or body.username))
    return LoginResponse(access_token=token)
@router.get("/me")
def me(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = verify_and_decode(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = str(claims.get("sub"))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    client = AccountClient()
    profile = client.get_account(user_id, authorization=authorization)
    if not profile or not profile.get("ok"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Return only needed fields to UI
    return {
        "user_id": profile.get("user_id"),
        "full_name": profile.get("full_name"),
        "phone_number": profile.get("phone_number"),
        "balance": profile.get("balance"),
    }
