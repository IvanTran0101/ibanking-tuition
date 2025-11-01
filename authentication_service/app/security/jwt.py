import hashlib
import hmac
import json
import time
import base64
from typing import Dict, Any

from authentication_service.app.settings import settings


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_access_token(subject: str, extra_claims: Dict[str, Any] | None = None) -> str:
    header = {"alg": settings.JWT_ALG, "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + settings.JWT_EXPIRES_MIN * 60,
    }
    if extra_claims:
        payload.update(extra_claims)

    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


"""
Auth-only helpers: token issuance and password hashing.
JWT verification has been moved to libs/security/jwt.py for shared use.
"""
