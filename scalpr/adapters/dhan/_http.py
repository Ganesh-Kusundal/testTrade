"""Dhan HTTP transport module with token-bucket rate limiter.

No circuit breaker. No Result monad. Uses exceptions for error flow.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.dhan.co/v2"

DHAN_BUCKETS: dict[str, dict[str, float | int]] = {
    "orders": {"rate": 3.0, "capacity": 5},
    "market_data": {"rate": 5.0, "capacity": 10},
    "portfolio": {"rate": 2.0, "capacity": 4},
    "history": {"rate": 2.0, "capacity": 4},
    "master": {"rate": 1.0 / 300.0, "capacity": 1},
}

PAPER_BUCKETS: dict[str, dict[str, float | int]] = {
    name: {"rate": 1_000_000.0, "capacity": 1_000_000}
    for name in ("orders", "market_data", "portfolio", "history", "master",
                 "quotes", "historical")
}


class DhanHttpError(Exception):
    """Base for all Dhan HTTP transport errors."""


class RateLimitTimeout(DhanHttpError):
    """Rate limiter could not acquire a token within the timeout."""


class DhanAuthError(DhanHttpError):
    """401 response from the API (after retry, token manager handles refresh)."""


class DhanRequestError(DhanHttpError):
    """4xx response from the API (excluding 401 and 429)."""

    def __init__(self, status: int, body: str, *args: Any) -> None:
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:200]}", *args)


class DhanServerError(DhanHttpError):
    """5xx response after exhausting retries."""

    def __init__(self, status: int, body: str, *args: Any) -> None:
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body[:200]}", *args)


@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float
    refill_period: float = 1.0

    tokens: float = field(init=False)
    _last_refill: float = field(default_factory=time.monotonic, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        self.tokens = float(self.capacity)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        tokens_per_second = self.refill_rate / self.refill_period
        self.tokens = min(float(self.capacity), self.tokens + elapsed * tokens_per_second)
        self._last_refill = now

    def acquire(self, tokens: int = 1, timeout: float = 0.5) -> bool:
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.001)


class RateLimiter:
    """Dhan-specific token-bucket rate limiter.

    Manages multiple named :class:`TokenBucket` instances keyed by the
    Dhan API usage category (orders, market_data, portfolio, history, master).
    """

    def __init__(
        self,
        buckets: dict[str, dict[str, float | int]] | None = None,
    ) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        for name, cfg in (buckets or DHAN_BUCKETS).items():
            self._buckets[name] = TokenBucket(
                capacity=int(cfg["capacity"]),
                refill_rate=float(cfg["rate"]),
                refill_period=1.0,
            )

    def acquire(self, bucket: str, tokens: int = 1, timeout: float = 0.5) -> bool:
        tb = self._buckets.get(bucket)
        if tb is None:
            raise ValueError(f"Unknown bucket: {bucket}")
        if not tb.acquire(tokens=tokens, timeout=timeout):
            raise RateLimitTimeout(
                f"Could not acquire {tokens} token(s) for bucket '{bucket}' "
                f"within {timeout}s"
            )
        return True


class DhanHttpClient:
    """Sync HTTP client for the Dhan REST API.

    Uses a :class:`RateLimiter` to throttle requests per bucket and a
    ``token_manager`` (any object with ``get_token() -> str``) to supply
    the Bearer token on every request.
    """

    def __init__(
        self,
        client_id: str,
        access_token: str,
        token_manager: Any,
        rate_limiter: RateLimiter | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.client_id = client_id
        self.access_token = access_token
        self.token_manager = token_manager
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._rate_limiter = rate_limiter or RateLimiter()
        self._session = requests.Session()

    def close(self) -> None:
        self._session.close()

    def get(self, path: str, bucket: str = "portfolio", **kwargs: Any) -> dict[str, Any]:
        return self._request("GET", path, bucket=bucket, **kwargs)

    def post(self, path: str, data: dict[str, Any] | None = None, bucket: str = "orders", **kwargs: Any) -> dict[str, Any]:
        return self._request("POST", path, json=data, bucket=bucket, **kwargs)

    def put(self, path: str, data: dict[str, Any] | None = None, bucket: str = "orders", **kwargs: Any) -> dict[str, Any]:
        return self._request("PUT", path, json=data, bucket=bucket, **kwargs)

    def delete(self, path: str, bucket: str = "orders", **kwargs: Any) -> dict[str, Any]:
        return self._request("DELETE", path, bucket=bucket, **kwargs)

    def _request(
        self,
        method: str,
        path: str,
        bucket: str = "orders",
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._rate_limiter.acquire(bucket)

        token = self.token_manager.get_token()

        # Dhan SDK adds dhanClientId to every POST/PUT body
        if method in ("POST", "PUT") and json is not None:
            json = {**json, "dhanClientId": self.client_id}

        url = f"{self._base_url}{path}" if path.startswith("/") else path
        headers = {
            "access-token": token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        max_retries = 2
        last_exc: Exception | None = None

        for attempt in range(max_retries):
            try:
                resp = self._session.request(
                    method,
                    url,
                    headers=headers,
                    json=json,
                    timeout=self._timeout,
                )
            except requests.RequestException as exc:
                last_exc = DhanServerError(0, str(exc))
                if attempt < max_retries - 1:
                    continue
                raise last_exc from exc

            if resp.status_code == 401:
                raise DhanAuthError(f"Token rejected on {method} {url}")

            if resp.status_code == 429:
                self._rate_limiter.acquire(bucket)
                continue

            if 400 <= resp.status_code < 500:
                raise DhanRequestError(resp.status_code, resp.text or "")

            if resp.status_code >= 500:
                if attempt < max_retries - 1:
                    continue
                raise DhanServerError(resp.status_code, resp.text or "")

            try:
                return resp.json()
            except Exception as exc:
                raise DhanHttpError(f"Invalid JSON response from {method} {url}") from exc

        if last_exc:
            raise last_exc
        raise DhanHttpError(f"Request failed after {max_retries} attempts: {method} {url}")
