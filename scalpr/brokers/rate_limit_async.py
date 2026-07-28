"""Asyncio port of the multi-bucket token-bucket rate limiter.

Plan Phase 5 (p5-async): same tables, same ``BucketConfig``, same
fail-fast deadline semantics as :mod:`scalpr.brokers.rate_limit` —
but every wait is ``asyncio.sleep`` so a 429 cooldown can never
stall the event loop. The sync versions are retained unchanged;
this module is purely additive.

State is loop-confined (asyncio is single-threaded), so mutations
need no threading locks; an ``asyncio.Lock`` guards the
refill/consume critical section for structural parity with the
sync implementation.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Mapping

from scalpr.brokers.rate_limit import BucketConfig


class AsyncTokenBucketRateLimiter:
    """Async token bucket with min_interval enforcement and 429 cooldown.

    Mirrors ``TokenBucketRateLimiter`` semantics exactly:
    - ``acquire(timeout=None)`` waits (cooperatively) until tokens refill;
    - ``acquire(timeout=T)`` fails fast — returns False if an active 429
      cooldown outlasts the deadline instead of sleeping through it;
    - ``trigger_cooldown()`` sets the cooldown window and halves the rate;
    - the original rate is restored after ``restore_cooldown`` seconds.
    """

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
        self._lock = asyncio.Lock()
        self._original_rate: float | None = None
        self._reduced_at: float | None = None
        self._restore_cooldown = restore_cooldown
        self._min_interval_s = min_interval_ms / 1000.0
        self._last_request_time: float = 0.0
        self._cooldown_until: float = 0.0
        self._cooldown_on_429_s = cooldown_on_429_s

    @property
    def rate(self) -> float:
        return self.config.rate_per_second

    @rate.setter
    def rate(self, value: float) -> None:
        if self._original_rate is None:
            self._original_rate = self.config.rate_per_second
        self.config.rate_per_second = value
        self._reduced_at = time.monotonic()

    def _maybe_restore_rate(self) -> None:
        """Restore original rate if cooldown has elapsed."""
        if self._reduced_at is None or self._original_rate is None:
            return
        elapsed = time.monotonic() - self._reduced_at
        if elapsed >= self._restore_cooldown:
            self.config.rate_per_second = self._original_rate
            self._reduced_at = None
            self._original_rate = None

    async def _check_cooldown(self, deadline: float | None = None) -> bool:
        """Handle an active 429 cooldown.

        With no deadline: await until the cooldown expires (cooperative —
        the event loop keeps running). With a deadline: fail fast — return
        False immediately if the cooldown outlasts the caller's budget.
        """
        cooldown_until = self._cooldown_until
        now = time.monotonic()
        if now >= cooldown_until:
            return True
        if deadline is not None and cooldown_until > deadline:
            return False
        await asyncio.sleep(cooldown_until - now)
        return True

    async def _check_min_interval(self) -> None:
        """Enforce minimum interval between requests."""
        if self._min_interval_s <= 0:
            return
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_interval_s:
            await asyncio.sleep(self._min_interval_s - elapsed)

    def trigger_cooldown(self) -> None:
        """Trigger cooldown after receiving HTTP 429."""
        self._cooldown_until = time.monotonic() + self._cooldown_on_429_s
        self.reduce_rate(0.5)

    async def acquire(self, tokens: int = 1, timeout: float | None = None) -> bool:
        self._maybe_restore_rate()
        deadline = (time.monotonic() + timeout) if timeout is not None else None
        if not await self._check_cooldown(deadline):
            return False
        await self._check_min_interval()
        if tokens > self._capacity:
            return False
        while True:
            async with self._lock:
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
            await asyncio.sleep(max(sleep_time, 0.001))

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


class AsyncRollingWindowCounter:
    """Async rolling-window counter for extra_windows enforcement.

    Same caps as ``RollingWindowCounter`` ("250/min", "7000/day") but
    the wait between slot polls is ``asyncio.sleep``.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max = max_requests
        self._window_s = window_seconds
        self._timestamps: deque[float] = deque()

    async def acquire(self, timeout: float | None = None) -> bool:
        """Wait until a request slot is available within the rolling window."""
        deadline = (time.monotonic() + timeout) if timeout is not None else None
        while True:
            self._prune()
            if len(self._timestamps) < self._max:
                self._timestamps.append(time.monotonic())
                return True
            if deadline is not None and time.monotonic() >= deadline:
                return False
            await asyncio.sleep(0.05)

    def _prune(self) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.monotonic() - self._window_s
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()


class AsyncMultiBucketRateLimiter:
    """Async multi-bucket rate limiter with rolling-window enforcement."""

    def __init__(
        self,
        configs: dict[str, BucketConfig],
        extra_windows: dict[str, list[tuple[int, float]]] | None = None,
        min_intervals_ms: dict[str, float] | None = None,
        cooldowns_on_429_s: dict[str, float] | None = None,
    ) -> None:
        min_intervals_ms = min_intervals_ms or {}
        cooldowns_on_429_s = cooldowns_on_429_s or {}
        self._buckets: dict[str, AsyncTokenBucketRateLimiter] = {}
        for k, v in configs.items():
            self._buckets[k] = AsyncTokenBucketRateLimiter(
                v,
                min_interval_ms=min_intervals_ms.get(k, 0),
                cooldown_on_429_s=cooldowns_on_429_s.get(k, 60.0),
            )
        self._categories = tuple(configs.keys())
        self._rolling: dict[str, list[AsyncRollingWindowCounter]] = {}
        if extra_windows:
            for bucket, windows in extra_windows.items():
                self._rolling[bucket] = [
                    AsyncRollingWindowCounter(max_req, window_s)
                    for max_req, window_s in windows
                ]

    def categories(self) -> list[str]:
        return list(self._categories)

    def get_bucket(self, category: str) -> AsyncTokenBucketRateLimiter:
        bucket = self._buckets.get(category)
        if bucket is None:
            raise ValueError(f"Unknown category: {category}")
        return bucket

    def _resolve(self, category: str) -> AsyncTokenBucketRateLimiter:
        bucket = self._buckets.get(category)
        if bucket is not None:
            return bucket
        fallback = self._buckets.get("admin")
        if fallback is not None:
            return fallback
        if self._buckets:
            return next(iter(self._buckets.values()))
        raise ValueError(f"Unknown category: {category}")

    async def acquire(self, category: str, tokens: int = 1, timeout: float | None = None) -> bool:
        # Rolling windows first — a slot is consumed even if the token
        # bucket then times out (deliberately conservative, same as sync).
        rolling_counters = self._rolling.get(category)
        if rolling_counters:
            for counter in rolling_counters:
                if not await counter.acquire(timeout=timeout):
                    return False
        return await self._resolve(category).acquire(tokens, timeout)

    def reduce_rate(self, category: str, factor: float) -> None:
        self._resolve(category).reduce_rate(factor)

    def trigger_cooldown(self, category: str) -> None:
        """Trigger 429 cooldown for a specific bucket."""
        self._resolve(category).trigger_cooldown()


def async_limiter_from_table(
    table: Mapping[str, Mapping[str, float | tuple[tuple[int, float], ...]]],
) -> AsyncMultiBucketRateLimiter:
    """Build AsyncMultiBucketRateLimiter from a rate-limit table.

    Consumes the exact same DHAN_RATE_LIMITS / PAPER_RATE_LIMITS tables
    as the sync ``limiter_from_table`` — one source of truth.
    """
    configs: dict[str, BucketConfig] = {}
    extra_windows: dict[str, list[tuple[int, float]]] = {}
    min_intervals_ms: dict[str, float] = {}
    cooldowns_on_429_s: dict[str, float] = {}
    for name, row in table.items():
        configs[name] = BucketConfig(
            rate_per_second=float(row["sustained_rps"]),
            capacity=int(row["burst_rps"]),
        )
        min_intervals_ms[name] = float(row.get("min_interval_ms", 0))
        cooldowns_on_429_s[name] = float(row.get("cooldown_on_429_s", 60.0))
        extra_raw = row.get("extra_windows")
        if extra_raw and isinstance(extra_raw, tuple):
            extra_windows[name] = list(extra_raw)
    return AsyncMultiBucketRateLimiter(
        configs,
        extra_windows=extra_windows if extra_windows else None,
        min_intervals_ms=min_intervals_ms,
        cooldowns_on_429_s=cooldowns_on_429_s,
    )


__all__ = [
    "AsyncMultiBucketRateLimiter",
    "AsyncRollingWindowCounter",
    "AsyncTokenBucketRateLimiter",
    "async_limiter_from_table",
]
