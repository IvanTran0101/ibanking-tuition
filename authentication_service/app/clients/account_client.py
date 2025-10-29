from typing import Optional, Dict, Any

from libs.http import HttpClient
from authentication_service.app.settings import settings


class AccountClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self._client = HttpClient(base_url or settings.ACCOUNT_SERVICE_URL)

    def verify_credentials(self, username: str, password_hash: str) -> Dict[str, Any]:
        """
        Calls account service to verify credentials.
        Expected response: {"ok": bool, "user_id": str | None}
        """
        payload = {"username": username, "password_hash": password_hash}
        # Endpoint path is a suggestion; adjust to match account service.
        resp = self._client.post("/internal/accounts/verify", json=payload)
        return resp.json()
