from pydantic import BaseModel


class VerifyRequest(BaseModel):
    username: str
    password_hash: str


class VerifyResponse(BaseModel):
    ok: bool
    user_id: str | None = None
    full_name: str | None = None
    phone_number: str | None = None
    balance: float | None = None
