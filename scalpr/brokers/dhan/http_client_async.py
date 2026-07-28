"""Async HTTP client for Dhan REST API (aiohttp).

Plan Phase 5 (p5-async): additive async counterpart of
:class:`scalpr.brokers.dhan.http_client.DhanHttpClient`. Identical
semantics — same endpoint→bucket map, orders-bucket fail-fast,
429 → trigger_cooldown + raise (never retry-in-line), 401/DH-906
refresh-once, exponential backoff on 5xx/transport errors — but
every wait is ``await asyncio.sleep`` and the limiter is the async
port, so sustained 429 cooldowns can never block the event loop.

The sync client remains the production default; this client is for
async call sites (FastAPI routes, async strategies).
"""

from __future__ import annotations

import asyncio
import json as jsonlib
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from config.endpoints import Dhan
from scalpr.brokers.dhan._http_common import (
    _MAX_RETRIES,
    _ORDERS_ACQUIRE_TIMEOUT_S,
    _REFRESH_COOLDOWN_SECONDS,
    backoff_delay,
    bucket_for,
    build_url,
    classify_response,
    try_refresh_token,
)
from scalpr.brokers.dhan.exceptions import (
    AuthenticationError,
    BrokerError,
    OrderError,
    RateLimitError,
)
from scalpr.brokers.dhan.http_client import CircuitBreaker
from scalpr.brokers.rate_limit import DHAN_RATE_LIMITS
from scalpr.brokers.rate_limit_async import (
    AsyncMultiBucketRateLimiter,
    async_limiter_from_table,
)

logger = logging.getLogger(__name__)


class AsyncDhanHttpClient:
    """Async HTTP client for Dhan API with retry, rate limiting, and circuit breaker.

    Shares the endpoint→bucket map, retry policy constants, and
    CircuitBreaker with the sync client — one source of truth.
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
        session: aiohttp.ClientSession | None = None,
        limiter: AsyncMultiBucketRateLimiter | None = None,
    ) -> None:
        self.client_id = client_id
        self.access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._token_refresh_fn = token_refresh_fn
        self._enable_retry = enable_retry
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._limiter = limiter or async_limiter_from_table(DHAN_RATE_LIMITS)
        self._session = session  # lazily created inside the running loop
        self._headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "client-id": client_id,
            "access-token": access_token,
        }
        self._last_refresh_time: float = 0.0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    def update_token(self, access_token: str) -> None:
        """Update access token used on subsequent requests."""
        self.access_token = access_token
        self._headers["access-token"] = access_token

    async def close(self) -> None:
        """Close the underlying HTTP session and release resources."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def post(self, endpoint: str, json: dict | None = None) -> dict[str, Any]:
        """POST request to Dhan API."""
        return await self._request("POST", endpoint, json=json)

    async def get(self, endpoint: str) -> dict[str, Any]:
        """GET request from Dhan API."""
        return await self._request("GET", endpoint)

    async def put(self, endpoint: str, json: dict | None = None) -> dict[str, Any]:
        """PUT request to Dhan API."""
        return await self._request("PUT", endpoint, json=json)

    async def delete(self, endpoint: str) -> dict[str, Any]:
        """DELETE request to Dhan API."""
        return await self._request("DELETE", endpoint)

    # Same prefix map as the sync client — single source of truth.
    _bucket_for = staticmethod(bucket_for)

    def _try_refresh_token(self) -> bool:
        """Attempt token refresh. Returns True if successful."""
        success, self._last_refresh_time = try_refresh_token(
            self._last_refresh_time,
            _REFRESH_COOLDOWN_SECONDS,
            self._token_refresh_fn,
            self.update_token,
            self.client_id,
        )
        return success

    async def _request(self, method: str, endpoint: str, json: dict | None = None) -> dict[str, Any]:
        """Execute HTTP request with retry, rate limiting, and circuit breaker."""
        # Circuit breaker check
        if not self._circuit_breaker.allow_request():
            raise BrokerError(f"Circuit breaker open: {method} {endpoint}")

        bucket = self._bucket_for(endpoint)
        if bucket == "orders":
            # Fail-fast on the order path: bounded wait, then reject.
            if not await self._limiter.acquire(bucket, timeout=_ORDERS_ACQUIRE_TIMEOUT_S):
                logger.warning("rate_limit_fail_fast", extra={
                    "method": method, "endpoint": endpoint, "bucket": bucket,
                })
                raise RateLimitError(
                    f"Rate limit budget exhausted for {method} {endpoint} "
                    f"(orders bucket, waited {_ORDERS_ACQUIRE_TIMEOUT_S}s)"
                )
        else:
            await self._limiter.acquire(bucket)
        url = build_url(self._base_url, endpoint)

        max_attempts = _MAX_RETRIES if self._enable_retry else 1
        last_exc: Exception | None = None
        session = await self._get_session()

        for attempt in range(1, max_attempts + 1):
            try:
                async with session.request(
                    method, url, json=json, headers=self._headers
                ) as resp:
                    status = resp.status
                    text = await resp.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_exc = BrokerError(f"HTTP {method} {url} failed: {exc}")
                self._circuit_breaker.record_failure()

                if attempt < max_attempts:
                    delay = backoff_delay(attempt)
                    logger.warning("http_retry", extra={
                        "method": method, "endpoint": endpoint, "attempt": attempt,
                        "delay_ms": int(delay * 1000),
                    })
                    await asyncio.sleep(delay)
                    continue
                raise last_exc from exc

            logger.debug("http_response", extra={
                "method": method, "endpoint": endpoint, "status": status,
            })

            category = classify_response(status, text or "")

            if category == "auth_rejected":
                if attempt == 1 and self._try_refresh_token():
                    logger.info("http_retry_after_refresh", extra={"method": method, "endpoint": endpoint})
                    continue
                raise AuthenticationError(
                    f"Token rejected: HTTP {status} on {method} {endpoint}"
                    + (" (DH-906 Invalid Token)" if status != 401 else "")
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
                        "method": method, "endpoint": endpoint, "status": status,
                        "attempt": attempt, "delay_ms": int(delay * 1000),
                    })
                    await asyncio.sleep(delay)
                    continue
                raise BrokerError(f"Dhan API {method} {url} failed: HTTP {status} — {text[:200]}")

            if category == "client_error":
                body = text[:300]
                logger.warning("http_client_error", extra={
                    "method": method, "endpoint": endpoint, "status": status, "body": body,
                })
                raise OrderError(f"Dhan API {method} {url} failed: HTTP {status} — {body}")

            # Success
            try:
                data = jsonlib.loads(text)
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

    # Same exponential backoff schedule as the sync client.
    _backoff_delay = staticmethod(backoff_delay)
