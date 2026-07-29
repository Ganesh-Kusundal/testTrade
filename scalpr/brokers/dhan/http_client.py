"""HTTP client for Dhan REST API with retry, rate limiting, and circuit breaker.

Adapted from Trade_XV2 with SCALPR-specific simplifications.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import requests

from config.endpoints import Dhan
from scalpr.brokers.dhan._http_common import (
    _MAX_RETRIES,
    _ORDERS_ACQUIRE_TIMEOUT_S,
    backoff_delay,
    bucket_for,
    build_url,
    classify_response,
    try_refresh_token,
)
from scalpr.brokers.dhan.auth import is_expiring_soon
from scalpr.brokers.dhan.exceptions import (
    AuthenticationError,
    BrokerError,
    OrderError,
    RateLimitError,
)
from scalpr.brokers.rate_limit import (
    DHAN_RATE_LIMITS,
    MultiBucketRateLimiter,
    limiter_from_table,
)

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker for fault isolation."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 5.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_state_change = time.time()
        self.lock = threading.Lock()

    def allow_request(self) -> bool:
        with self.lock:
            now = time.time()
            if self.state == "OPEN":
                if now - self.last_state_change > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    self.last_state_change = now
                    return True
                return False
            return True

    def record_success(self) -> None:
        with self.lock:
            self.failure_count = 0
            self.state = "CLOSED"
            self.last_state_change = time.time()

    def record_failure(self) -> None:
        with self.lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_state_change = time.time()


class DhanHttpClient:
    """Sync HTTP client for Dhan API with retry, rate limiting, and circuit breaker.

    Features:
    - Automatic retry with exponential backoff
    - Rate limiting per endpoint
    - Circuit breaker for fault isolation
    - Token refresh on 401
    - Comprehensive error handling
    """

    def __init__(
        self,
        client_id: str,
        access_token: str,
        base_url: str = Dhan.REST_BASE,
        timeout: float = 15.0,
        token_refresh_fn: Callable[[], str] | None = None,
        enable_retry: bool = True,
        circuit_breaker: CircuitBreaker | None = None,
        session: requests.Session | None = None,
        limiter: MultiBucketRateLimiter | None = None,
    ) -> None:
        self.client_id = client_id
        self.access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token_refresh_fn = token_refresh_fn
        self._enable_retry = enable_retry
        self._circuit_breaker = circuit_breaker or CircuitBreaker()

        # Use provided session or create new one
        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()
            self._session.headers.update({
                "Accept": "application/json",
                "Content-Type": "application/json",
            })

        self._session.headers.update({
            "client-id": client_id,
            "access-token": access_token,
        })
        self._limiter: MultiBucketRateLimiter = limiter or limiter_from_table(DHAN_RATE_LIMITS)

    def update_token(self, access_token: str) -> None:
        """Update access token in session headers."""
        self.access_token = access_token
        self._session.headers["access-token"] = access_token

    def close(self) -> None:
        """Close the underlying HTTP session and release resources."""
        self._session.close()

    def post(self, endpoint: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST request to Dhan API."""
        return self._request("POST", endpoint, json=json)

    def get(self, endpoint: str) -> dict[str, Any]:
        """GET request from Dhan API."""
        return self._request("GET", endpoint)

    def put(self, endpoint: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """PUT request to Dhan API."""
        return self._request("PUT", endpoint, json=json)

    def delete(self, endpoint: str) -> dict[str, Any]:
        """DELETE request to Dhan API."""
        return self._request("DELETE", endpoint)

    @staticmethod
    def _bucket_for(endpoint: str) -> str:
        """Resolve endpoint to rate-limit bucket name via prefix match."""
        return bucket_for(endpoint)

    def _try_refresh_token(self, force: bool = False) -> bool:
        """Attempt token refresh. Returns True if successful.

        When ``force`` is True (e.g. after a 401), the ``is_expiring_soon``
        guard is bypassed — a broker rejection means the token is invalid
        regardless of its JWT expiry.

        Cooldown is enforced by the TOTP cooldown guard (single source of truth).
        """
        return try_refresh_token(
            self._token_refresh_fn,
            self.update_token,
            self.client_id,
            is_expiring_soon_fn=None if force else lambda: is_expiring_soon(self.access_token),
        )

    def _request(self, method: str, endpoint: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute HTTP request with retry, rate limiting, and circuit breaker."""
        # Circuit breaker check
        if not self._circuit_breaker.allow_request():
            raise BrokerError(f"Circuit breaker open: {method} {endpoint}")

        bucket = self._bucket_for(endpoint)
        if bucket == "orders":
            # Fail-fast on the order path: bounded wait, then reject.
            if not self._limiter.acquire(bucket, timeout=_ORDERS_ACQUIRE_TIMEOUT_S):
                raise RateLimitError(
                    f"Rate limit budget exhausted for {method} {endpoint} "
                    f"(orders bucket, waited {_ORDERS_ACQUIRE_TIMEOUT_S}s)"
                )
        else:
            self._limiter.acquire(bucket)
        url = build_url(self._base_url, endpoint)

        max_attempts = _MAX_RETRIES if self._enable_retry else 1
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                resp = self._session.request(method, url, json=json, timeout=self._timeout)
            except requests.RequestException as exc:
                last_exc = BrokerError(f"HTTP {method} {url} failed: {exc}")
                self._circuit_breaker.record_failure()

                if attempt < max_attempts:
                    delay = backoff_delay(attempt)
                    logger.warning("http_retry", extra={
                        "method": method, "endpoint": endpoint, "attempt": attempt,
                        "delay_ms": int(delay * 1000),
                    })
                    time.sleep(delay)
                    continue
                raise last_exc from exc

            logger.debug("http_response", extra={
                "method": method, "endpoint": endpoint, "status": resp.status_code,
            })

            category = classify_response(resp.status_code, resp.text or "")

            if category == "auth_rejected":
                # 401 = token rejected by broker. Force refresh regardless of
                # JWT expiry — a broker rejection means the token is invalid
                # even if it hasn't expired locally.
                if attempt == 1 and self._try_refresh_token(force=True):
                    logger.info("http_retry_after_refresh", extra={"method": method, "endpoint": endpoint})
                    continue
                raise AuthenticationError(
                    f"Token rejected: HTTP {resp.status_code} on {method} {endpoint}"
                    + (" (DH-906 Invalid Token)" if resp.status_code != 401 else "")
                )

            if category == "rate_limited":
                self._limiter.trigger_cooldown(bucket)
                logger.warning("http_rate_limited", extra={
                    "method": method, "endpoint": endpoint, "bucket": bucket,
                })
                raise RateLimitError(f"Rate limited: HTTP 429 on {method} {endpoint}")

            if category == "server_error":
                self._circuit_breaker.record_failure()
                if attempt < max_attempts:
                    delay = backoff_delay(attempt)
                    logger.warning("http_server_error_retry", extra={
                        "method": method, "endpoint": endpoint, "status": resp.status_code,
                        "attempt": attempt, "delay_ms": int(delay * 1000),
                    })
                    time.sleep(delay)
                    continue
                body = resp.text[:200]
                raise BrokerError(f"Dhan API {method} {url} failed: HTTP {resp.status_code} — {body}")

            if category == "client_error":
                body = resp.text[:300]
                logger.warning("http_client_error", extra={
                    "method": method, "endpoint": endpoint, "status": resp.status_code, "body": body,
                })
                raise OrderError(f"Dhan API {method} {url} failed: HTTP {resp.status_code} — {body}")

            # Success
            try:
                data = resp.json()
            except Exception as exc:
                raise BrokerError(f"Invalid JSON from {method} {url}") from exc

            if isinstance(data, dict) and data.get("status") == "failure":
                remarks = data.get("remarks", "unknown error")
                self._circuit_breaker.record_failure()
                raise OrderError(f"API failure: {remarks}")

            self._circuit_breaker.record_success()
            return data  # type: ignore[no-any-return]

        if last_exc:
            raise last_exc
        raise BrokerError(f"Request failed after {max_attempts} attempts: {method} {url}")

    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        """Exponential backoff: 500ms, 1s, 2s, 4s... capped at 5s."""
        return backoff_delay(attempt)
