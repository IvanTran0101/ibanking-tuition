import hmac
from typing import Optional


def verify_password_hash(stored_hash: str, provided_hash: str) -> bool:
    """
    Constant-time compare for password hashes.

    In this architecture, authentication_service is responsible for hashing the
    plaintext password with its salt and sending the hash to account_service for
    verification against the stored hash. Therefore, account_service only needs
    to compare two hashes without knowing the salt.
    """
    if stored_hash is None or provided_hash is None:
        return False
    # Use constant-time compare to avoid timing side-channels.
    try:
        return hmac.compare_digest(stored_hash, provided_hash)
    except Exception:
        return False
