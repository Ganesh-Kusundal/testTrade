"""Order submission rate limiting — prevents runaway strategies from spamming orders."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from scalpr.domain.errors import OrderRateLimitExceeded  # noqa: F401 — re-export


@dataclass
class OrderRateLimitConfig:
    """Configuration for order rate limiting."""
    max_orders_per_second: float = 10.0
    burst_capacity: int = 10


class OrderRateLimiter:
    """Token bucket rate limiter for order submission frequency.

    Non-blocking: acquire() returns False immediately if limit exceeded.
    Thread-safe.
    """

    def __init__(self, config: OrderRateLimitConfig | None = None) -> None:
        self.config = config or OrderRateLimitConfig()
        self._tokens = float(self.config.burst_capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        """Try to acquire a token. Returns True if allowed, False if rate limited."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill

            # Refill tokens based on elapsed time
            self._tokens = min(
                float(self.config.burst_capacity),
                self._tokens + elapsed * self.config.max_orders_per_second
            )
            self._last_refill = now

            # Check if we have a token available
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    @property
    def tokens_available(self) -> float:
        """Current token count (for monitoring/debugging)."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            return min(
                float(self.config.burst_capacity),
                self._tokens + elapsed * self.config.max_orders_per_second
            )
