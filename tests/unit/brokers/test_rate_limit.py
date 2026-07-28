"""Tests for the multi-bucket rate-limit framework (ported from Trade_XV2).

Covers: token-bucket burst/refill, min_interval spacing, 429 cooldown with
rate reduction + restore, rolling-window caps, bucket routing/fallback, and
DhanHttpClient wiring (acquire before request, trigger_cooldown on 429).
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from scalpr.brokers.dhan.exceptions import RateLimitError
from scalpr.brokers.dhan.http_client import DhanHttpClient
from scalpr.brokers.rate_limit import (
    DHAN_RATE_LIMITS,
    PAPER_RATE_LIMITS,
    BucketConfig,
    MultiBucketRateLimiter,
    RollingWindowCounter,
    TokenBucketRateLimiter,
    limiter_from_table,
)

# ============================================================================
# TokenBucketRateLimiter
# ============================================================================

class TestTokenBucket:
    def test_burst_capacity_allows_immediate_acquires(self):
        limiter = TokenBucketRateLimiter(BucketConfig(rate_per_second=10.0, capacity=5))
        start = time.monotonic()
        for _ in range(5):
            assert limiter.acquire()
        assert time.monotonic() - start < 0.1

    def test_acquire_blocks_until_refill(self):
        limiter = TokenBucketRateLimiter(BucketConfig(rate_per_second=20.0, capacity=1))
        assert limiter.acquire()
        start = time.monotonic()
        assert limiter.acquire()  # must wait ~50ms for one token
        assert time.monotonic() - start >= 0.03

    def test_acquire_timeout_returns_false(self):
        limiter = TokenBucketRateLimiter(BucketConfig(rate_per_second=0.5, capacity=1))
        assert limiter.acquire()
        assert limiter.acquire(timeout=0.05) is False

    def test_acquire_more_than_capacity_returns_false(self):
        limiter = TokenBucketRateLimiter(BucketConfig(rate_per_second=10.0, capacity=2))
        assert limiter.acquire(tokens=3) is False

    def test_min_interval_enforced(self):
        limiter = TokenBucketRateLimiter(
            BucketConfig(rate_per_second=100.0, capacity=100),
            min_interval_ms=50,
        )
        assert limiter.acquire()
        start = time.monotonic()
        assert limiter.acquire()
        assert time.monotonic() - start >= 0.04

    def test_trigger_cooldown_halves_rate_and_blocks(self):
        limiter = TokenBucketRateLimiter(
            BucketConfig(rate_per_second=100.0, capacity=100),
            cooldown_on_429_s=0.1,
        )
        limiter.trigger_cooldown()
        assert limiter.rate == pytest.approx(50.0)
        start = time.monotonic()
        assert limiter.acquire()
        assert time.monotonic() - start >= 0.08

    def test_rate_restored_after_cooldown(self):
        limiter = TokenBucketRateLimiter(
            BucketConfig(rate_per_second=100.0, capacity=100),
            restore_cooldown=0.05,
            cooldown_on_429_s=0.0,
        )
        limiter.reduce_rate(0.5)
        assert limiter.rate == pytest.approx(50.0)
        time.sleep(0.06)
        limiter.acquire()
        assert limiter.rate == pytest.approx(100.0)

    def test_invalid_config_rejected(self):
        with pytest.raises(ValueError):
            BucketConfig(rate_per_second=0)
        with pytest.raises(ValueError):
            BucketConfig(capacity=0)

    def test_concurrent_trigger_cooldown_and_acquire_race(self):
        """trigger_cooldown from one thread must never corrupt limiter state
        while other threads spin on acquire (post lock-hygiene fix)."""
        import threading

        limiter = TokenBucketRateLimiter(
            BucketConfig(rate_per_second=200.0, capacity=50),
            cooldown_on_429_s=0.01,
            restore_cooldown=0.01,
        )
        errors: list[Exception] = []
        stop = threading.Event()

        def acquirer():
            try:
                while not stop.is_set():
                    limiter.acquire(timeout=0.02)
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        def cooler():
            try:
                while not stop.is_set():
                    limiter.trigger_cooldown()
                    time.sleep(0.002)
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        threads = [threading.Thread(target=acquirer) for _ in range(4)]
        threads.append(threading.Thread(target=cooler))
        for t in threads:
            t.start()
        time.sleep(0.3)
        stop.set()
        for t in threads:
            t.join(timeout=2)
        assert not errors
        assert not any(t.is_alive() for t in threads), "deadlocked thread detected"
        # invariant: token count never exceeds capacity
        assert limiter._tokens <= limiter._capacity + 1e-9


# ============================================================================
# RollingWindowCounter
# ============================================================================

class TestRollingWindow:
    def test_allows_up_to_max_within_window(self):
        counter = RollingWindowCounter(max_requests=3, window_seconds=10.0)
        for _ in range(3):
            assert counter.acquire(timeout=0.01)
        assert counter.acquire(timeout=0.01) is False

    def test_slot_frees_after_window_expires(self):
        counter = RollingWindowCounter(max_requests=1, window_seconds=0.1)
        assert counter.acquire(timeout=0.01)
        assert counter.acquire(timeout=0.01) is False
        time.sleep(0.12)
        assert counter.acquire(timeout=0.01)


# ============================================================================
# MultiBucketRateLimiter
# ============================================================================

class TestMultiBucket:
    def _limiter(self, **extra):
        configs = {
            "orders": BucketConfig(rate_per_second=100.0, capacity=100),
            "admin": BucketConfig(rate_per_second=100.0, capacity=100),
        }
        return MultiBucketRateLimiter(configs, **extra)

    def test_acquire_known_category(self):
        assert self._limiter().acquire("orders")

    def test_unknown_category_falls_back_to_admin(self):
        limiter = self._limiter()
        assert limiter.acquire("nonexistent")
        with pytest.raises(ValueError):
            limiter.get_bucket("nonexistent")

    def test_rolling_window_blocks_category(self):
        limiter = self._limiter(extra_windows={"orders": [(2, 60.0)]})
        assert limiter.acquire("orders", timeout=0.01)
        assert limiter.acquire("orders", timeout=0.01)
        assert limiter.acquire("orders", timeout=0.01) is False
        # other buckets unaffected
        assert limiter.acquire("admin", timeout=0.01)

    def test_trigger_cooldown_targets_single_bucket(self):
        limiter = self._limiter()
        limiter.trigger_cooldown("orders")
        assert limiter.get_bucket("orders").rate == pytest.approx(50.0)
        assert limiter.get_bucket("admin").rate == pytest.approx(100.0)


# ============================================================================
# limiter_from_table
# ============================================================================

class TestLimiterFromTable:
    def test_dhan_table_builds_all_buckets(self):
        limiter = limiter_from_table(DHAN_RATE_LIMITS)
        assert set(limiter.categories()) == set(DHAN_RATE_LIMITS.keys())

    def test_dhan_table_applies_extended_fields(self):
        limiter = limiter_from_table(DHAN_RATE_LIMITS)
        orders = limiter.get_bucket("orders")
        assert orders._min_interval_s == pytest.approx(0.1)
        assert orders._cooldown_on_429_s == pytest.approx(130.0)
        # orders bucket has 250/min and 7000/day rolling windows
        assert len(limiter._rolling["orders"]) == 2

    def test_paper_table_has_no_throttling_delays(self):
        limiter = limiter_from_table(PAPER_RATE_LIMITS)
        start = time.monotonic()
        for _ in range(50):
            assert limiter.acquire("orders")
        assert time.monotonic() - start < 0.5


# ============================================================================
# DhanHttpClient wiring
# ============================================================================

def _resp(status_code, payload=None, text=""):
    resp = MagicMock(status_code=status_code, text=text)
    resp.json.return_value = payload if payload is not None else {}
    return resp


def _client(session, limiter):
    session.headers = {}
    return DhanHttpClient(
        client_id="cid", access_token="tok",
        session=session, limiter=limiter,
    )


class TestHttpClientWiring:
    def test_acquire_called_with_mapped_bucket(self):
        session = MagicMock()
        session.request.return_value = _resp(200, {"ok": True})
        limiter = MagicMock()
        limiter.acquire.return_value = True
        client = _client(session, limiter)

        client.post("/orders", json={})

        limiter.acquire.assert_called_once()
        assert limiter.acquire.call_args.args[0] == "orders"

    def test_429_triggers_bucket_cooldown_and_raises(self):
        session = MagicMock()
        session.request.return_value = _resp(429)
        limiter = MagicMock()
        client = _client(session, limiter)

        with pytest.raises(RateLimitError, match="429"):
            client.get("/marketfeed/quote")

        limiter.trigger_cooldown.assert_called_once_with("quotes")
        # no in-line retry against a hard limit
        assert session.request.call_count == 1

    def test_unmapped_endpoint_uses_admin_bucket(self):
        session = MagicMock()
        session.request.return_value = _resp(200, {"ok": True})
        limiter = MagicMock()
        client = _client(session, limiter)

        client.get("/fundlimit")

        limiter.acquire.assert_called_once_with("admin")


# ============================================================================
# Orders-bucket fail-fast (Phase 1): the order path may fail fast but must
# NEVER sleep through a 429 cooldown (up to 130s) inside acquire().
# ============================================================================

class TestCooldownFailFast:
    def test_acquire_with_timeout_fails_fast_during_cooldown(self):
        """acquire(timeout=...) during an active 429 cooldown must return
        False quickly instead of sleeping through the cooldown."""
        limiter = TokenBucketRateLimiter(
            BucketConfig(rate_per_second=100.0, capacity=100),
            cooldown_on_429_s=30.0,
        )
        limiter.trigger_cooldown()
        start = time.monotonic()
        assert limiter.acquire(timeout=0.2) is False
        assert time.monotonic() - start < 1.0

    def test_multibucket_acquire_timeout_fails_fast_during_cooldown(self):
        limiter = limiter_from_table(DHAN_RATE_LIMITS)
        limiter.trigger_cooldown("orders")  # 130s cooldown per Dhan spec
        start = time.monotonic()
        assert limiter.acquire("orders", timeout=0.2) is False
        assert time.monotonic() - start < 1.0

    def test_acquire_without_timeout_still_waits_out_cooldown(self):
        """Blocking semantics preserved for non-order paths (timeout=None)."""
        limiter = TokenBucketRateLimiter(
            BucketConfig(rate_per_second=100.0, capacity=100),
            cooldown_on_429_s=0.1,
        )
        limiter.trigger_cooldown()
        start = time.monotonic()
        assert limiter.acquire()
        assert time.monotonic() - start >= 0.08


class TestOrdersFailFastWiring:
    def test_orders_endpoint_acquires_with_timeout(self):
        """The orders bucket must be acquired with a short fail-fast timeout."""
        session = MagicMock()
        session.request.return_value = _resp(200, {"ok": True})
        limiter = MagicMock()
        limiter.acquire.return_value = True
        client = _client(session, limiter)

        client.post("/orders", json={})

        args, kwargs = limiter.acquire.call_args
        assert args[0] == "orders"
        timeout = kwargs.get("timeout")
        assert timeout is not None and 0 < timeout <= 5.0

    def test_orders_acquire_failure_raises_rate_limit_error(self):
        """acquire returning False must surface as RateLimitError — the
        request must never be sent and never silently hang."""
        session = MagicMock()
        limiter = MagicMock()
        limiter.acquire.return_value = False
        client = _client(session, limiter)

        with pytest.raises(RateLimitError):
            client.post("/orders", json={})
        session.request.assert_not_called()

    def test_order_submission_during_real_cooldown_fails_fast(self):
        """End-to-end: after a 429 cooldown, the next order POST raises
        RateLimitError in well under the 130s cooldown."""
        session = MagicMock()
        session.request.return_value = _resp(200, {"ok": True})
        limiter = limiter_from_table(DHAN_RATE_LIMITS)
        limiter.trigger_cooldown("orders")
        client = _client(session, limiter)

        start = time.monotonic()
        with pytest.raises(RateLimitError):
            client.post("/orders", json={})
        assert time.monotonic() - start < 1.0
        session.request.assert_not_called()
