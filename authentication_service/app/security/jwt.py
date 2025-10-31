import base64
import hashlib
import hmac
import json
import time
from typing import Dict, Any, Tuple

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


def _b64url_decode(segment: str) -> bytes:
    padding = '=' * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def verify_and_decode(token: str) -> Dict[str, Any]:
    """
    Verifies HMAC-SHA256 JWT and returns payload dict.
    Raises ValueError on invalid/expired tokens.
    """
    try:
        header_b64, payload_b64, sig_b64 = token.split('.')
    except ValueError:
        raise ValueError("invalid token format")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("invalid signature")

    payload = json.loads(_b64url_decode(payload_b64))
    now = int(time.time())
    if "exp" in payload and int(payload["exp"]) < now:
        raise ValueError("token expired")
    return payload
