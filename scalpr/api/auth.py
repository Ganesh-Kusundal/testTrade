"""Stdlib HS256 JWT auth — Bloomberg plan Module 10 (API security).

No third-party dependency: hmac + hashlib + base64url + json + time.
Enabled only when SCALPR_JWT_SECRET is set; dev/paper boots without the
secret stay open so existing flows are unchanged. Fail-closed on every
non-exempt route once enabled.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Any

# Health probes must stay reachable without a token (k8s/monitoring).
EXEMPT_PATHS = frozenset({
    "/health", "/health/live", "/health/ready",
    "/api/v1/health", "/api/v1/health/live", "/api/v1/health/ready",
})


class AuthError(Exception):
    """Token verification failure — always maps to 401, never 500."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(subject: str, secret: str, expires_in_s: int = 86400) -> str:
    """Mint a signed HS256 JWT: header.payload.signature."""
    now = int(time.time())
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(json.dumps(
        {"sub": subject, "iat": now, "exp": now + expires_in_s}
    ).encode())
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url_encode(sig)}"


def verify_token(token: str, secret: str) -> dict[str, Any]:
    """Verify signature + expiry; return claims. Raises AuthError otherwise."""
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("malformed token")
    header_b64, payload_b64, sig_b64 = parts

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    try:
        provided = _b64url_decode(sig_b64)
    except Exception as e:
        raise AuthError("malformed signature") from e
    if not hmac.compare_digest(expected, provided):
        raise AuthError("invalid signature")

    try:
        claims = json.loads(_b64url_decode(payload_b64))
    except Exception as e:
        raise AuthError("malformed payload") from e
    exp = claims.get("exp")
    if exp is None or time.time() >= exp:
        raise AuthError("token expired")
    return claims  # type: ignore[no-any-return]


def _extract_token(scope: Any) -> str | None:
    """Bearer header for http; header or ?token= query param for websocket."""
    headers = dict(scope.get("headers") or [])
    auth = headers.get(b"authorization", b"").decode("latin-1")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]  # type: ignore[no-any-return]
    if scope["type"] == "websocket":
        from urllib.parse import parse_qs
        qs = parse_qs((scope.get("query_string") or b"").decode("latin-1"))
        values = qs.get("token")
        if values:
            return values[0]  # type: ignore[no-any-return]
    return None


class JwtAuthMiddleware:
    """Pure-ASGI middleware: 401 on missing/invalid token, health exempt."""

    def __init__(self, app: Any, secret: str) -> None:
        self.app = app
        self.secret = secret

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path in EXEMPT_PATHS or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        token = _extract_token(scope)
        try:
            if token is None:
                raise AuthError("missing token")
            verify_token(token, self.secret)
        except AuthError as e:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 4401})
            else:
                body = json.dumps({"detail": str(e)}).encode()
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"www-authenticate", b"Bearer"),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
