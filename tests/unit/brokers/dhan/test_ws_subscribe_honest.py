"""S-3 (B-015): subscribe() must report per-symbol truth.

Before this fix, subscribe() returned a single True even when every symbol
failed resolution and nothing was sent to the SDK — strategies then waited
forever for ticks that could never arrive. Unknown exchanges also silently
defaulted to NSE_EQ, streaming wrong-segment (or no) data.
"""
from unittest.mock import MagicMock

import pytest

from scalpr.brokers.dhan.ws_client import (
    DhanWebSocketClient,
    _exchange_to_segment_int,
)


@pytest.fixture
def mock_resolver():
    resolver = MagicMock()
    inst = MagicMock()
    inst.security_id = 2885
    resolver.resolve.return_value = inst
    resolver.wire_segment_of.return_value = "NSE_EQ"
    return resolver


def _connected_client(resolver) -> tuple[DhanWebSocketClient, MagicMock]:
    client = DhanWebSocketClient(
        access_token="t", client_id="c", resolver=resolver
    )
    feed = MagicMock()
    client._feed = feed
    client._connected = True
    return client, feed


class TestSubscribePerSymbolResults:
    async def test_all_success(self, mock_resolver):
        client, feed = _connected_client(mock_resolver)
        result = await client.subscribe([("RELIANCE", "NSE")])
        assert result == {("RELIANCE", "NSE"): True}
        feed.subscribe_symbols.assert_called_once()

    async def test_resolution_failure_reported_false(self, mock_resolver):
        mock_resolver.resolve.side_effect = ValueError("Unknown symbol")
        client, feed = _connected_client(mock_resolver)
        result = await client.subscribe([("UNKNOWN", "NSE")])
        assert result == {("UNKNOWN", "NSE"): False}
        feed.subscribe_symbols.assert_not_called()

    async def test_mixed_results(self, mock_resolver):
        def resolve(symbol, exchange):
            if symbol == "BAD":
                raise ValueError("Unknown symbol")
            inst = MagicMock()
            inst.security_id = 2885
            return inst

        mock_resolver.resolve.side_effect = resolve
        client, _feed = _connected_client(mock_resolver)
        result = await client.subscribe([("RELIANCE", "NSE"), ("BAD", "NSE")])
        assert result[("RELIANCE", "NSE")] is True
        assert result[("BAD", "NSE")] is False

    async def test_already_subscribed_counts_as_true(self, mock_resolver):
        client, feed = _connected_client(mock_resolver)
        first = await client.subscribe([("RELIANCE", "NSE")])
        second = await client.subscribe([("RELIANCE", "NSE")])
        assert first == {("RELIANCE", "NSE"): True}
        assert second == {("RELIANCE", "NSE"): True}
        # SDK only called once — the dedup path still reports honest truth
        feed.subscribe_symbols.assert_called_once()

    async def test_no_resolver_non_numeric_symbol_reported_false(self):
        client, feed = _connected_client(None)
        result = await client.subscribe([("RELIANCE", "NSE")])
        assert result == {("RELIANCE", "NSE"): False}
        feed.subscribe_symbols.assert_not_called()

    async def test_no_resolver_numeric_security_id_works(self):
        client, _feed = _connected_client(None)
        result = await client.subscribe([("2885", "NSE")])
        assert result == {("2885", "NSE"): True}


class TestUnknownExchangeFailsClosed:
    def test_known_exchanges_map(self):
        assert _exchange_to_segment_int("NSE") == 1
        assert _exchange_to_segment_int("MCX") == 5

    def test_unknown_exchange_raises(self):
        """No silent NSE_EQ default: a typo'd exchange must fail loudly."""
        with pytest.raises(ValueError, match="unknown exchange"):
            _exchange_to_segment_int("NASDAQ")

    async def test_subscribe_unknown_exchange_reported_false(self):
        client, feed = _connected_client(None)
        result = await client.subscribe([("2885", "NASDAQ")])
        assert result == {("2885", "NASDAQ"): False}
        feed.subscribe_symbols.assert_not_called()
