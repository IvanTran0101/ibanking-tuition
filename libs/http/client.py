# libs/http/client.py
from __future__ import annotations
import os, json, uuid
from typing import Any, Dict, Optional
import requests

# Header constants
CID_HEADER = "X-Correlation-Id"
IDEMP_HEADER = "Idempotency-Key"

def _gen_cid() -> str:
    """Sinh correlation-id ngẫu nhiên nếu chưa có."""
    return str(uuid.uuid4())


class HttpError(Exception):
    """Exception cho HTTP lỗi (status >= 400)."""
    def __init__(self, status: int, url: str, body: Any, correlation_id: Optional[str] = None):
        super().__init__(f"HTTP {status} {url} (cid={correlation_id})")
        self.status = status
        self.url = url
        self.body = body
        self.correlation_id = correlation_id


class HttpClient:
    """
    Client cực gọn cho internal call giữa services.
    - Hỗ trợ GET/POST/PUT/DELETE
    - Auto JSON encode/decode
    - Timeout
    - Propagate X-Correlation-Id
    - Optional Idempotency-Key
    """

    def __init__(self, base_url: str, *, timeout_sec: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.s = requests.Session()
        self.s.headers.update({"Accept": "application/json"})

    # ---- generic request helper ----
    def _request(self,
                 method: str,
                 path: str,
                 *,
                 params: Dict[str, Any] | None = None,
                 json_body: Dict[str, Any] | None = None,
                 headers: Dict[str, str] | None = None,
                 correlation_id: str | None = None,
                 idempotency_key: str | None = None) -> Any:

        url = f"{self.base_url}/{path.lstrip('/')}"
        hdrs = {**(headers or {})}

        # Correlation-ID
        cid = correlation_id or hdrs.get(CID_HEADER) or _gen_cid()
        hdrs[CID_HEADER] = cid

        # Idempotency-Key (nếu có)
        if idempotency_key:
            hdrs[IDEMP_HEADER] = idempotency_key

        # JSON body
        data = None
        if json_body is not None:
            hdrs.setdefault("Content-Type", "application/json")
            data = json.dumps(json_body)

        # Gửi request
        resp = self.s.request(method, url, params=params, data=data, headers=hdrs, timeout=self.timeout_sec)

        # Nếu lỗi → raise HttpError
        if resp.status_code >= 400:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise HttpError(resp.status_code, url, body, correlation_id=cid)

        # Decode JSON nếu có
        if "application/json" in resp.headers.get("Content-Type", ""):
            return resp.json()
        return resp.text or None

    # ---- public shortcut methods ----
    def get(self, path: str, **kwargs): return self._request("GET", path, **kwargs)
    def post(self, path: str, **kwargs): return self._request("POST", path, **kwargs)
    def put(self, path: str, **kwargs): return self._request("PUT", path, **kwargs)
    def delete(self, path: str, **kwargs): return self._request("DELETE", path, **kwargs)


# ---- factory helpers cho từng service (đọc ENV) ----
def make_account_client() -> HttpClient:
    return HttpClient(os.getenv("ACCOUNT_SERVICE_URL", "http://account-service:8080"))

def make_payment_client() -> HttpClient:
    return HttpClient(os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8080"))

def make_tuition_client() -> HttpClient:
    return HttpClient(os.getenv("TUITION_SERVICE_URL", "http://tuition-service:8080"))

def make_otp_client() -> HttpClient:
    return HttpClient(os.getenv("OTP_SERVICE_URL", "http://otp-service:8080"))
