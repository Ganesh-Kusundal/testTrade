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
from scalpr.brokers.dhan.exceptions import (
    AuthenticationError,
    BrokerError,
    OrderError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

# Rate limits per endpoint (seconds between requests)
# Aligned with Dhan API rate limits:
# - Order APIs: 10/sec, 250/min
# - Data APIs: 5/sec
# - Quote APIs: 1/sec
_RATE_LIMITS: dict[str, float] = {
    "/marketfeed/quote": 1.0,   # 1 req/sec (Quote APIs)
    "/marketfeed/ltp": 0.2,     # 5 req/sec (Data APIs)
    "/marketfeed/ohlc": 0.2,    # 5 req/sec (Data APIs)
    "/optionchain": 1.0,        # 1 req/sec (Quote APIs)
    "/charts/": 0.2,            # 5 req/sec (Data APIs)
    "/orders": 0.1,             # 10 req/sec (Order APIs)
}

# Retry configuration
_MAX_RETRIES = 3
_BASE_DELAY_MS = 500
_MAX_DELAY_MS = 5000
_REFRESH_COOLDOWN_SECONDS = 60


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
        self._last_request_time: dict[str, float] = {}
        self._rate_lock = threading.Lock()
        self._last_refresh_time: float = 0.0

    def update_token(self, access_token: str) -> None:
        """Update access token in session headers."""
        self.access_token = access_token
        self._session.headers["access-token"] = access_token

    def post(self, endpoint: str, json: dict | None = None) -> dict[str, Any]:
        """POST request to Dhan API."""
        return self._request("POST", endpoint, json=json)

    def get(self, endpoint: str) -> dict[str, Any]:
        """GET request from Dhan API."""
        return self._request("GET", endpoint)

    def put(self, endpoint: str, json: dict | None = None) -> dict[str, Any]:
        """PUT request to Dhan API."""
        return self._request("PUT", endpoint, json=json)

    def delete(self, endpoint: str) -> dict[str, Any]:
        """DELETE request to Dhan API."""
        return self._request("DELETE", endpoint)

    def _throttle(self, endpoint: str) -> None:
        """Apply rate limiting for endpoint."""
        interval = self._match_rate_limit(endpoint, _RATE_LIMITS)
        if interval <= 0:
            return
        with self._rate_lock:
            last = self._last_request_time.get(endpoint, 0.0)
            elapsed = time.time() - last
            if elapsed < interval:
                time.sleep(interval - elapsed)
            self._last_request_time[endpoint] = time.time()

    @staticmethod
    def _match_rate_limit(endpoint: str, limits: dict[str, float]) -> float:
        """Match endpoint against rate limit keys using prefix matching."""
        if endpoint in limits:
            return limits[endpoint]
        for prefix, interval in limits.items():
            if endpoint.startswith(prefix):
                return interval
        return 0

    def _try_refresh_token(self) -> bool:
        """Attempt token refresh. Returns True if successful."""
        now = time.time()
        
        if now - self._last_refresh_time < _REFRESH_COOLDOWN_SECONDS:
            logger.debug("token_refresh_skipped: cooldown_active")
            return False
            
        if self._token_refresh_fn is None:
            return False
            
        try:
            new_token = self._token_refresh_fn()
            if new_token:
                self._last_refresh_time = now
                self.update_token(new_token)
                logger.info("token_refreshed", extra={"client_id": self.client_id})
                return True
        except Exception as exc:
            logger.warning("token_refresh_failed", extra={"error": str(exc)})
            
        return False

    def _request(self, method: str, endpoint: str, json: dict | None = None) -> dict[str, Any]:
        """Execute HTTP request with retry, rate limiting, and circuit breaker."""
        # Circuit breaker check
        if not self._circuit_breaker.allow_request():
            raise BrokerError(f"Circuit breaker open: {method} {endpoint}")

        self._throttle(endpoint)
        url = f"{self._base_url}{endpoint}" if endpoint.startswith("/") else endpoint

        max_attempts = _MAX_RETRIES if self._enable_retry else 1
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                resp = self._session.request(method, url, json=json, timeout=self._timeout)
            except requests.RequestException as exc:
                last_exc = BrokerError(f"HTTP {method} {url} failed: {exc}")
                self._circuit_breaker.record_failure()
                
                if attempt < max_attempts:
                    delay = self._backoff_delay(attempt)
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

            # 401 - try token refresh
            if resp.status_code == 401:
                if attempt == 1 and self._try_refresh_token():
                    logger.info("http_retry_after_refresh", extra={"method": method, "endpoint": endpoint})
                    continue
                raise AuthenticationError(f"Token rejected: HTTP 401 on {method} {endpoint}")

            # 429 - rate limited
            if resp.status_code == 429:
                if attempt < max_attempts:
                    delay = self._backoff_delay(attempt)
                    logger.warning("http_rate_limited_retry", extra={
                        "method": method, "endpoint": endpoint, "attempt": attempt, 
                        "delay_ms": int(delay * 1000),
                    })
                    time.sleep(delay)
                    continue
                raise RateLimitError(f"Rate limited: HTTP 429 on {method} {endpoint}")

            # 5xx - server error, retry
            if resp.status_code >= 500:
                self._circuit_breaker.record_failure()
                if attempt < max_attempts:
                    delay = self._backoff_delay(attempt)
                    logger.warning("http_server_error_retry", extra={
                        "method": method, "endpoint": endpoint, "status": resp.status_code,
                        "attempt": attempt, "delay_ms": int(delay * 1000),
                    })
                    time.sleep(delay)
                    continue
                body = resp.text[:200]
                raise BrokerError(f"Dhan API {method} {url} failed: HTTP {resp.status_code} — {body}")

            # 4xx - client error (no retry)
            if resp.status_code >= 400:
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
            return data

        if last_exc:
            raise last_exc
        raise BrokerError(f"Request failed after {max_attempts} attempts: {method} {url}")

    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        """Exponential backoff: 500ms, 1s, 2s, 4s... capped at 5s."""
        delay_ms = min(_BASE_DELAY_MS * (2 ** (attempt - 1)), _MAX_DELAY_MS)
        return delay_ms / 1000.0

    def close(self) -> None:
        """Close HTTP session."""
        self._session.close()
