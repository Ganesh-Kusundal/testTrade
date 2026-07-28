"""Multi-bucket token-bucket rate limiting for broker HTTP.

Ported from Trade_XV2 (v2/src/plugins/brokers/common/rate_limit.py):
token buckets with sustained/burst RPS, min_interval enforcement,
429 cooldown with rate reduction, and rolling-window caps
(e.g. Dhan's 250 orders/min and 7000 orders/day).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass

# Rate limit tables — sustained_rps/burst_rps drive the token bucket;
# min_interval_ms enforces spacing; cooldown_on_429_s is the mandatory
# back-off after HTTP 429; extra_windows are rolling caps (max, seconds).

DHAN_RATE_LIMITS: dict[str, dict[str, float | tuple[tuple[int, float], ...]]] = {
    "orders": {
        "sustained_rps": 10.0,
        "burst_rps": 20.0,
        "min_interval_ms": 100,
        "cooldown_on_429_s": 130,
        "extra_windows": ((250, 60.0), (7000, 86400.0)),
    },
    "quotes": {
        "sustained_rps": 1.0,
        "burst_rps": 2.0,
        "min_interval_ms": 1000,
        "cooldown_on_429_s": 130,
    },
    # /optionchain has its own quota: 1 request per 3 seconds (Dhan documented
    # limit). Sharing the "quotes" bucket (1/s) would systematically overdrive
    # the endpoint under sustained polling.
    "optionchain": {
        "sustained_rps": 0.33,
        "burst_rps": 1.0,
        "min_interval_ms": 3000,
        "cooldown_on_429_s": 130,
    },
    "historical": {
        "sustained_rps": 5.0,
        "burst_rps": 10.0,
        "min_interval_ms": 200,
        "cooldown_on_429_s": 130,
    },
    "options_historical": {
        "sustained_rps": 2.0,
        "burst_rps": 3.0,
        "min_interval_ms": 500,
        "cooldown_on_429_s": 130,
    },
    "expired_historical": {
        "sustained_rps": 5.0,
        "burst_rps": 10.0,
        "min_interval_ms": 200,
        "cooldown_on_429_s": 60,
    },
    "admin": {
        "sustained_rps": 10.0,
        "burst_rps": 20.0,
        "min_interval_ms": 100,
        "cooldown_on_429_s": 130,
    },
}

PAPER_RATE_LIMITS: dict[str, dict[str, float]] = {
    "orders": {"sustained_rps": 1000.0, "burst_rps": 1000.0, "min_interval_ms": 0, "cooldown_on_429_s": 0},
    "quotes": {"sustained_rps": 1000.0, "burst_rps": 1000.0, "min_interval_ms": 0, "cooldown_on_429_s": 0},
    "historical": {"sustained_rps": 1000.0, "burst_rps": 1000.0, "min_interval_ms": 0, "cooldown_on_429_s": 0},
    "admin": {"sustained_rps": 1000.0, "burst_rps": 1000.0, "min_interval_ms": 0, "cooldown_on_429_s": 0},
}


@dataclass
class BucketConfig:
    """Token-bucket parameters: refill rate and burst capacity."""

    rate_per_second: float = 10.0
    capacity: int = 10

    def __post_init__(self) -> None:
        if self.rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")


class TokenBucketRateLimiter:
    """Token bucket with min_interval enforcement and 429 cooldown support."""

    def __init__(
        self,
        config: BucketConfig | None = None,
        restore_cooldown: float = 60.0,
        min_interval_ms: float = 0,
        cooldown_on_429_s: float = 60.0,
    ) -> None:
        self.config = config or BucketConfig()
        self._tokens = float(self.config.capacity)
        self._last_refill_nanos = time.monotonic_ns()
        self._capacity = float(self.config.capacity)
        self._lock = threading.Lock()
        self._original_rate: float | None = None
        self._reduced_at: float | None = None
        self._restore_cooldown = restore_cooldown
        # min_interval between requests, cooldown on 429
        self._min_interval_s = min_interval_ms / 1000.0
        self._last_request_time: float = 0.0
        self._cooldown_until: float = 0.0
        self._cooldown_on_429_s = cooldown_on_429_s

    @property
    def rate(self) -> float:
        return self.config.rate_per_second

    @rate.setter
    def rate(self, value: float) -> None:
        with self._lock:
            if self._original_rate is None:
                self._original_rate = self.config.rate_per_second
            self.config.rate_per_second = value
            self._reduced_at = time.monotonic()

    def _maybe_restore_rate(self) -> None:
        """Restore original rate if cooldown has elapsed."""
        with self._lock:
            if self._reduced_at is None or self._original_rate is None:
                return
            elapsed = time.monotonic() - self._reduced_at
            if elapsed >= self._restore_cooldown:
                self.config.rate_per_second = self._original_rate
                self._reduced_at = None
                self._original_rate = None

    def _check_cooldown(self, deadline: float | None = None) -> bool:
        """Handle an active 429 cooldown.

        With no deadline: sleep until the cooldown expires (legacy blocking
        semantics for non-critical paths). With a deadline: fail fast —
        return False immediately if the cooldown outlasts the caller's
        budget instead of sleeping through it (order path must never block).
        """
        with self._lock:
            cooldown_until = self._cooldown_until
        now = time.monotonic()
        if now >= cooldown_until:
            return True
        if deadline is not None and cooldown_until > deadline:
            return False
        time.sleep(cooldown_until - now)
        return True

    def _check_min_interval(self) -> None:
        """Enforce minimum interval between requests."""
        if self._min_interval_s <= 0:
            return
        with self._lock:
            last_request_time = self._last_request_time
        now = time.monotonic()
        elapsed = now - last_request_time
        if elapsed < self._min_interval_s:
            sleep_time = self._min_interval_s - elapsed
            time.sleep(sleep_time)

    def trigger_cooldown(self) -> None:
        """Trigger cooldown after receiving HTTP 429."""
        with self._lock:
            self._cooldown_until = time.monotonic() + self._cooldown_on_429_s
        # reduce_rate → rate setter takes the (non-reentrant) lock itself.
        self.reduce_rate(0.5)

    def acquire(self, tokens: int = 1, timeout: float | None = None) -> bool:
        self._maybe_restore_rate()
        deadline = (time.monotonic() + timeout) if timeout is not None else None
        if not self._check_cooldown(deadline):
            return False
        self._check_min_interval()
        if tokens > self._capacity:
            return False
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    self._last_request_time = time.monotonic()
                    return True
            if deadline is not None and time.monotonic() >= deadline:
                return False
            sleep_time = min(
                timeout if timeout is not None else 0.001,
                1.0 / self.config.rate_per_second if self.config.rate_per_second > 0 else 0.001,
            )
            time.sleep(max(sleep_time, 0.001))

    def _refill(self) -> None:
        now_ns = time.monotonic_ns()
        elapsed_sec = (now_ns - self._last_refill_nanos) / 1_000_000_000.0
        if elapsed_sec > 0:
            self._tokens = min(
                self._capacity,
                self._tokens + elapsed_sec * self.config.rate_per_second,
            )
            self._last_refill_nanos = now_ns

    def reduce_rate(self, factor: float) -> None:
        """Reduce rate by factor (e.g. 0.5 = halve)."""
        self.rate = self.rate * factor


class RollingWindowCounter:
    """Rolling-window rate counter for extra_windows enforcement.

    Tracks request timestamps and enforces caps like "250/min" or "7000/day".
    Thread-safe via internal lock.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max = max_requests
        self._window_s = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self, timeout: float | None = None) -> bool:
        """Wait until a request slot is available within the rolling window."""
        deadline = (time.monotonic() + timeout) if timeout is not None else None
        while True:
            with self._lock:
                self._prune()
                if len(self._timestamps) < self._max:
                    self._timestamps.append(time.monotonic())
                    return True
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(0.05)

    def _prune(self) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.monotonic() - self._window_s
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()


class MultiBucketRateLimiter:
    """Multi-bucket rate limiter with optional rolling-window enforcement."""

    def __init__(
        self,
        configs: dict[str, BucketConfig],
        extra_windows: dict[str, list[tuple[int, float]]] | None = None,
        min_intervals_ms: dict[str, float] | None = None,
        cooldowns_on_429_s: dict[str, float] | None = None,
    ) -> None:
        min_intervals_ms = min_intervals_ms or {}
        cooldowns_on_429_s = cooldowns_on_429_s or {}
        self._buckets: dict[str, TokenBucketRateLimiter] = {}
        for k, v in configs.items():
            self._buckets[k] = TokenBucketRateLimiter(
                v,
                min_interval_ms=min_intervals_ms.get(k, 0),
                cooldown_on_429_s=cooldowns_on_429_s.get(k, 60.0),
            )
        self._categories = tuple(configs.keys())
        # Rolling-window counters for extra_windows (e.g. 250/min, 7000/day)
        self._rolling: dict[str, list[RollingWindowCounter]] = {}
        if extra_windows:
            for bucket, windows in extra_windows.items():
                self._rolling[bucket] = [
                    RollingWindowCounter(max_req, window_s)
                    for max_req, window_s in windows
                ]

    def categories(self) -> list[str]:
        return list(self._categories)

    def get_bucket(self, category: str) -> TokenBucketRateLimiter:
        bucket = self._buckets.get(category)
        if bucket is None:
            raise ValueError(f"Unknown category: {category}")
        return bucket

    def _resolve(self, category: str) -> TokenBucketRateLimiter:
        bucket = self._buckets.get(category)
        if bucket is not None:
            return bucket
        fallback = self._buckets.get("admin")
        if fallback is not None:
            return fallback
        if self._buckets:
            return next(iter(self._buckets.values()))
        raise ValueError(f"Unknown category: {category}")

    def acquire(self, category: str, tokens: int = 1, timeout: float | None = None) -> bool:
        # Check rolling windows first (if any). NOTE: a rolling-window slot is
        # consumed even if the token bucket then times out — deliberately
        # conservative: we under-count remaining quota rather than risk
        # exceeding a hard broker cap (e.g. 7000 orders/day).
        rolling_counters = self._rolling.get(category)
        if rolling_counters:
            for counter in rolling_counters:
                if not counter.acquire(timeout=timeout):
                    return False
        return self._resolve(category).acquire(tokens, timeout)

    def reduce_rate(self, category: str, factor: float) -> None:
        self._resolve(category).reduce_rate(factor)

    def trigger_cooldown(self, category: str) -> None:
        """Trigger 429 cooldown for a specific bucket."""
        self._resolve(category).trigger_cooldown()


def limiter_from_table(
    table: Mapping[str, Mapping[str, float | tuple[tuple[int, float], ...]]],
) -> MultiBucketRateLimiter:
    """Build MultiBucketRateLimiter from a rate-limit table with extended fields."""
    configs: dict[str, BucketConfig] = {}
    extra_windows: dict[str, list[tuple[int, float]]] = {}
    min_intervals_ms: dict[str, float] = {}
    cooldowns_on_429_s: dict[str, float] = {}
    for name, row in table.items():
        configs[name] = BucketConfig(
            rate_per_second=float(row["sustained_rps"]),  # type: ignore[arg-type]
            capacity=int(row["burst_rps"]),  # type: ignore[arg-type]
        )
        min_intervals_ms[name] = float(row.get("min_interval_ms", 0))  # type: ignore[arg-type]
        cooldowns_on_429_s[name] = float(row.get("cooldown_on_429_s", 60.0))  # type: ignore[arg-type]
        extra_raw = row.get("extra_windows")
        if extra_raw and isinstance(extra_raw, tuple):
            extra_windows[name] = list(extra_raw)
    return MultiBucketRateLimiter(
        configs,
        extra_windows=extra_windows if extra_windows else None,
        min_intervals_ms=min_intervals_ms,
        cooldowns_on_429_s=cooldowns_on_429_s,
    )


__all__ = [
    "DHAN_RATE_LIMITS",
    "PAPER_RATE_LIMITS",
    "BucketConfig",
    "MultiBucketRateLimiter",
    "RollingWindowCounter",
    "TokenBucketRateLimiter",
    "limiter_from_table",
]
