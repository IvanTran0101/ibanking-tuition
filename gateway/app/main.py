from __future__ import annotations

import uuid
from typing import Dict, Iterable

import httpx
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from libs.security.jwt import verify_and_decode
from gateway.app.settings import settings


HOP_BY_HOP_HEADERS: set[str] = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

ACCOUNT_URL = settings.ACCOUNT_SERVICE_URL.rstrip("/")
PAYMENT_URL = settings.PAYMENT_SERVICE_URL.rstrip("/")
TUITION_URL = settings.TUITION_SERVICE_URL.rstrip("/")
OTP_URL = settings.OTP_SERVICE_URL.rstrip("/")
NOTIF_URL = settings.NOTIFICATION_SERVICE_URL.rstrip("/")


app = FastAPI(title="Gateway")

# Configure CORS from settings
origins_cfg = settings.CORS_ALLOW_ORIGINS
origins = ["*"] if origins_cfg.strip() == "*" else [o.strip() for o in origins_cfg.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


_client: httpx.AsyncClient | None = None


@app.on_event("startup")
async def _startup() -> None:
    global _client
    _client = httpx.AsyncClient(timeout=httpx.Timeout(settings.HTTP_TIMEOUT))


@app.on_event("shutdown")
async def _shutdown() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        finally:
            _client = None


def _filtered_headers(headers: Iterable[tuple[str, str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in headers:
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS or lk == "host":
            continue
        out[k] = v
    return out


async def _require_user(request: Request) -> str:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        claims = verify_and_decode(token, key=settings.JWT_SECRET, alg=settings.JWT_ALG)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = str(claims.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return user_id


async def _proxy(request: Request, base_url: str, tail: str, *, require_auth: bool = True) -> Response:
    global _client
    assert _client is not None

    x_user_id = None
    if require_auth:
        x_user_id = await _require_user(request)

    cid = request.headers.get("correlation-id") or str(uuid.uuid4())

    # Build outgoing headers
    headers = _filtered_headers(request.headers.items())
    headers["correlation-id"] = cid
    if x_user_id:
        headers["X-User-Id"] = x_user_id

    # Forward request
    url = f"{base_url}/{tail}" if tail else base_url
    try:
        body = await request.body()
        resp = await _client.request(
            request.method,
            url,
            content=body if body else None,
            headers=headers,
            params=dict(request.query_params),
        )
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Upstream unavailable")

    # Build response, filter hop-by-hop headers
    resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}
    return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers, media_type=resp.headers.get("content-type"))


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.api_route("/account/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_account(path: str, request: Request) -> Response:
    return await _proxy(request, ACCOUNT_URL, path)


@app.api_route("/payment/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_payment(path: str, request: Request) -> Response:
    return await _proxy(request, PAYMENT_URL, path)


@app.api_route("/tuition/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_tuition(path: str, request: Request) -> Response:
    return await _proxy(request, TUITION_URL, path)


@app.api_route("/otp/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_otp(path: str, request: Request) -> Response:
    return await _proxy(request, OTP_URL, path)


@app.api_route("/notifications/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_notifications(path: str, request: Request) -> Response:
    # Usually safe to require auth here too; relax by passing require_auth=False if needed
    return await _proxy(request, NOTIF_URL, path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "gateway.app.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=False,
        workers=1,
    )
