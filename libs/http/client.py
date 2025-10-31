from __future__ import annotations

"""HTTP client for sync/async calls with correlation-id and simple retries.

Standardizes inter-service HTTP calls across services using httpx.
"""

import asyncio
import os
import time
import uuid
from typing import Any, Dict, Optional, TYPE_CHECKING

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

if TYPE_CHECKING:
    import httpx as _httpx  # type: ignore
    ResponseT = _httpx.Response
else:  # at runtime when httpx may be missing, keep a loose alias
    ResponseT = Any


DEFAULT_TIMEOUT = float(os.getenv("HTTP_CLIENT_TIMEOUT", "5.0"))
DEFAULT_RETRIES = int(os.getenv("HTTP_CLIENT_RETRIES", "3"))
BACKOFF_FACTOR = float(os.getenv("HTTP_CLIENT_BACKOFF", "0.2"))

CORRELATION_HEADER = "correlation-id"


def _build_url(base_url: str, url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if not base_url:
        return url
    return f"{base_url.rstrip('/')}/{url.lstrip('/')}"


class HttpClient:
    def __init__(
        self,
        base_url: str = "",
        *,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        if httpx is None:
            raise RuntimeError("httpx is required for HttpClient; please install it.")
        self.base_url = base_url
        self.timeout = httpx.Timeout(timeout)
        self.retries = max(1, retries)
        self._default_headers = default_headers or {}
        self._client = httpx.Client(timeout=self.timeout)

    def _headers(self, headers: Optional[Dict[str, str]], correlation_id: Optional[str]) -> Dict[str, str]:
        h = dict(self._default_headers)
        if headers:
            h.update(headers)
        h.setdefault(CORRELATION_HEADER, correlation_id or str(uuid.uuid4()))
        return h

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        retries: Optional[int] = None,
    ) -> ResponseT:
        if httpx is None:
            raise RuntimeError("httpx is required for HttpClient; please install it.")
        attempts = max(1, retries or self.retries)
        last_exc: Optional[Exception] = None
        full_url = _build_url(self.base_url, url)
        for attempt in range(attempts):
            try:
                resp = self._client.request(
                    method,
                    full_url,
                    params=params,
                    json=json,
                    headers=self._headers(headers, correlation_id),
                )
                resp.raise_for_status()
                return resp
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as ex:
                last_exc = ex
                if attempt >= attempts - 1:
                    raise
                time.sleep(BACKOFF_FACTOR * (2 ** attempt))
        assert last_exc is not None
        raise last_exc

    def get(self, url: str, **kwargs: Any) -> ResponseT:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> ResponseT:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> ResponseT:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> ResponseT:
        return self.request("DELETE", url, **kwargs)

    def close(self) -> None:
        self._client.close()

    # --- helpers to manage default headers (e.g., Authorization) ---
    def set_default_headers(self, headers: Dict[str, str]) -> None:
        """Merge given headers into this client's default headers."""
        self._default_headers.update(headers or {})

    def set_bearer_token(self, token: str | None) -> None:
        """Set or clear the Authorization Bearer token for all requests."""
        if token:
            self._default_headers["Authorization"] = f"Bearer {token}"
        else:
            self._default_headers.pop("Authorization", None)


class AsyncHttpClient:
    def __init__(
        self,
        base_url: str = "",
        *,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ) -> None:
        if httpx is None:
            raise RuntimeError("httpx is required for AsyncHttpClient; please install it.")
        self.base_url = base_url
        self.timeout = httpx.Timeout(timeout)
        self.retries = max(1, retries)
        self._default_headers = default_headers or {}
        self._client = httpx.AsyncClient(timeout=self.timeout)

    def _headers(self, headers: Optional[Dict[str, str]], correlation_id: Optional[str]) -> Dict[str, str]:
        h = dict(self._default_headers)
        if headers:
            h.update(headers)
        h.setdefault(CORRELATION_HEADER, correlation_id or str(uuid.uuid4()))
        return h

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        retries: Optional[int] = None,
    ) -> ResponseT:
        if httpx is None:
            raise RuntimeError("httpx is required for AsyncHttpClient; please install it.")
        attempts = max(1, retries or self.retries)
        last_exc: Optional[Exception] = None
        full_url = _build_url(self.base_url, url)
        for attempt in range(attempts):
            try:
                resp = await self._client.request(
                    method,
                    full_url,
                    params=params,
                    json=json,
                    headers=self._headers(headers, correlation_id),
                )
                resp.raise_for_status()
                return resp
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as ex:
                last_exc = ex
                if attempt >= attempts - 1:
                    raise
                await asyncio.sleep(BACKOFF_FACTOR * (2 ** attempt))
        assert last_exc is not None
        raise last_exc

    async def get(self, url: str, **kwargs: Any) -> ResponseT:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> ResponseT:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> ResponseT:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> ResponseT:
        return await self.request("DELETE", url, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()

    # --- helpers to manage default headers (e.g., Authorization) ---
    def set_default_headers(self, headers: Dict[str, str]) -> None:
        """Merge given headers into this client's default headers."""
        self._default_headers.update(headers or {})

    def set_bearer_token(self, token: str | None) -> None:
        """Set or clear the Authorization Bearer token for all requests."""
        if token:
            self._default_headers["Authorization"] = f"Bearer {token}"
        else:
            self._default_headers.pop("Authorization", None)


# Factory helpers from env (sync clients)
def make_account_client() -> HttpClient:
    return HttpClient(os.getenv("ACCOUNT_SERVICE_URL", "http://account-service:8080"))


def make_payment_client() -> HttpClient:
    return HttpClient(os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8080"))


def make_tuition_client() -> HttpClient:
    return HttpClient(os.getenv("TUITION_SERVICE_URL", "http://tuition-service:8080"))


def make_otp_client() -> HttpClient:
    return HttpClient(os.getenv("OTP_SERVICE_URL", "http://otp-service:8080"))


__all__ = [
    "HttpClient",
    "AsyncHttpClient",
    "make_account_client",
    "make_payment_client",
    "make_tuition_client",
    "make_otp_client",
]
