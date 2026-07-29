"""Unit tests for TokenRefreshScheduler."""

from __future__ import annotations

import time

from scalpr.brokers.dhan._token_lifecycle import TokenBroadcast, TokenRefreshScheduler


class TestTokenRefreshScheduler:
    def test_refresh_now_calls_ensure_token(self):
        scheduler = TokenRefreshScheduler(
            broker_id="test",
            ensure_token_fn=lambda: "fresh_token",
            current_token_fn=lambda: "old_token",
        )
        result = scheduler.refresh_now()
        assert result is True
        assert scheduler.refresh_count == 1

    def test_broadcast_on_token_change(self):
        bc = TokenBroadcast()
        received: list[str] = []
        bc.register(lambda t: received.append(t))

        scheduler = TokenRefreshScheduler(
            broker_id="test",
            ensure_token_fn=lambda: "new_token",
            current_token_fn=lambda: "old_token",
            broadcast=bc,
        )
        scheduler.refresh_now()
        assert received == ["new_token"]

    def test_no_broadcast_when_token_unchanged(self):
        bc = TokenBroadcast()
        received: list[str] = []
        bc.register(lambda t: received.append(t))

        scheduler = TokenRefreshScheduler(
            broker_id="test",
            ensure_token_fn=lambda: "same_token",
            current_token_fn=lambda: "same_token",
            broadcast=bc,
        )
        scheduler.refresh_now()
        assert received == []

    def test_error_increments_error_count(self):
        def failing_ensure() -> str:
            raise RuntimeError("mint failed")

        scheduler = TokenRefreshScheduler(
            broker_id="test",
            ensure_token_fn=failing_ensure,
            current_token_fn=lambda: "",
        )
        result = scheduler.refresh_now()
        assert result is False
        assert scheduler.error_count == 1

    def test_start_stop(self):
        scheduler = TokenRefreshScheduler(
            broker_id="test",
            ensure_token_fn=lambda: "token",
            current_token_fn=lambda: "token",
            interval_seconds=0.1,
        )
        scheduler.start()
        assert scheduler.is_running
        time.sleep(0.05)
        scheduler.stop()
        assert not scheduler.is_running

    def test_start_idempotent(self):
        scheduler = TokenRefreshScheduler(
            broker_id="test",
            ensure_token_fn=lambda: "token",
            current_token_fn=lambda: "token",
        )
        scheduler.start()
        scheduler.start()  # should not create a second thread
        assert scheduler.is_running
        scheduler.stop()
