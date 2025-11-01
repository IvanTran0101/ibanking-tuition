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
