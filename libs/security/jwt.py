from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def verify_and_decode(
    token: str,
    *,
    key: Optional[str] = None,
    alg: str = "HS256",
    iss: Optional[str] = None,
    aud: Optional[str] = None,
    leeway: int = 0,
) -> Dict[str, Any]:
    """
    Verify an HMAC JWT (default HS256) and return payload as dict.

    - key: HMAC secret. If not provided, reads from ENV `JWT_SECRET`.
    - iss/aud (optional): validate issuer/audience when provided.
    - leeway: extra seconds allowed for clock skew on `exp`.
    """
    if alg != "HS256":
        raise ValueError("only HS256 is supported by this helper")

    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise ValueError("invalid token format")

    # Resolve key
    secret = key if key is not None else os.getenv("JWT_SECRET")
    if not secret:
        raise ValueError("JWT secret not configured; set JWT_SECRET or pass key")

    # Verify signature
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("invalid signature")

    # Decode payload and validate standard claims
    try:
        payload: Dict[str, Any] = json.loads(_b64url_decode(payload_b64))
    except Exception as ex:
        raise ValueError("invalid payload") from ex

    now = int(time.time())
    if "exp" in payload:
        if int(payload["exp"]) + int(leeway) < now:
            raise ValueError("token expired")
    if iss is not None and payload.get("iss") != iss:
        raise ValueError("invalid issuer")
    if aud is not None:
        aud_claim = payload.get("aud")
        if aud_claim != aud and (not isinstance(aud_claim, list) or aud not in aud_claim):
            raise ValueError("invalid audience")

    return payload


__all__ = ["verify_and_decode"]

