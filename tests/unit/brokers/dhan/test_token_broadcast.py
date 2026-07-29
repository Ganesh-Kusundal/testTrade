"""Unit tests for TokenBroadcast."""

from __future__ import annotations

import logging

from scalpr.brokers.dhan._token_lifecycle import TokenBroadcast


class TestTokenBroadcast:
    def test_broadcast_delivers_to_all(self):
        bc = TokenBroadcast()
        received: list[str] = []
        bc.register(lambda t: received.append(f"a:{t}"))
        bc.register(lambda t: received.append(f"b:{t}"))
        bc.broadcast("tok123")
        assert received == ["a:tok123", "b:tok123"]

    def test_broadcast_empty_token_noop(self):
        bc = TokenBroadcast()
        received: list[str] = []
        bc.register(lambda t: received.append(t))
        assert bc.broadcast("") == 0
        assert received == []

    def test_receiver_failure_isolated(self, caplog):
        bc = TokenBroadcast()
        received: list[str] = []

        def bad_receiver(token: str) -> None:
            raise RuntimeError("boom")

        bc.register(bad_receiver)
        bc.register(lambda t: received.append(t))

        with caplog.at_level(logging.WARNING):
            delivered = bc.broadcast("tok")

        assert delivered == 1
        assert received == ["tok"]

    def test_idempotent_registration(self):
        bc = TokenBroadcast()
        def fn(t):
            return None
        bc.register(fn)
        bc.register(fn)
        assert bc.receiver_count == 1

    def test_unregister(self):
        bc = TokenBroadcast()
        def fn(t):
            return None
        bc.register(fn)
        bc.unregister(fn)
        assert bc.receiver_count == 0

    def test_unregister_not_registered_is_noop(self):
        bc = TokenBroadcast()
        bc.unregister(lambda t: None)  # should not raise

    def test_unregister_all(self):
        bc = TokenBroadcast()
        bc.register(lambda t: None)
        bc.register(lambda t: None)
        count = bc.unregister_all()
        assert count == 2
        assert bc.receiver_count == 0

    def test_receiver_count(self):
        bc = TokenBroadcast()
        assert bc.receiver_count == 0
        bc.register(lambda t: None)
        assert bc.receiver_count == 1
