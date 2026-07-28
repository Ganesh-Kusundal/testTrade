"""C4 regression: Gateway↔WS bridge must use real ws_manager API on a live loop.

Autospec'd DhanWebSocketManager guarantees wrong call signatures fail here
(the original bug: gateway called subscribe(symbol, exchange) against
subscribe(self, symbols: list[str])).
"""
import asyncio
import threading
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.brokers.dhan.ws_manager import DhanWebSocketManager
from scalpr.brokers.gateway import Gateway
from scalpr.domain.tick import Tick


def _tick(symbol: str = "RELIANCE") -> Tick:
    return Tick(
        symbol=symbol,
        ltp=Decimal("2500"),
        bid=Decimal("2499"),
        ask=Decimal("2501"),
        delta_volume=1,
        cumulative_volume=100,
        exchange_timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def gateway_with_mock_manager():
    mgr = create_autospec(DhanWebSocketManager, instance=True)
    g = object.__new__(Gateway)
    g._broker_name = "dhan"
    g._config = {}
    g._gateway = create_autospec(IBrokerGateway, instance=True)
    g._stream_callbacks = []
    g._ws_lock = threading.Lock()
    g._ws_manager = mgr
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    g._ws_loop = loop
    g._ws_thread = thread
    yield g, mgr
    if g._ws_loop is not None:
        g._ws_loop.call_soon_threadsafe(g._ws_loop.stop)
        g._ws_thread.join(timeout=5)
        g._ws_loop.close()


def test_stream_subscribes_pairs_on_ws_loop(gateway_with_mock_manager):
    g, mgr = gateway_with_mock_manager
    g.stream("RELIANCE", callback=lambda t: None)
    mgr.subscribe_pairs.assert_awaited_once_with([("RELIANCE", "NSE")])


def test_stream_multiple_symbols_custom_exchange(gateway_with_mock_manager):
    g, mgr = gateway_with_mock_manager
    g.stream(["GOLD", "SILVER"], exchange="MCX")
    mgr.subscribe_pairs.assert_awaited_once_with([("GOLD", "MCX"), ("SILVER", "MCX")])


def test_dispatch_tick_delivers_to_all_callbacks(gateway_with_mock_manager):
    g, _ = gateway_with_mock_manager
    received: list[Tick] = []
    g._stream_callbacks.extend([received.append, received.append])
    tick = _tick()
    g._dispatch_tick(tick)
    assert received == [tick, tick]


def test_dispatch_tick_survives_broken_callback(gateway_with_mock_manager):
    g, _ = gateway_with_mock_manager
    received: list[Tick] = []

    def broken(tick: Tick) -> None:
        raise RuntimeError("boom")

    g._stream_callbacks.extend([broken, received.append])
    g._dispatch_tick(_tick())
    assert len(received) == 1


def test_stop_stream_stops_manager_and_joins_thread(gateway_with_mock_manager):
    g, mgr = gateway_with_mock_manager
    thread = g._ws_thread
    g.stop_stream()
    mgr.stop.assert_awaited_once()
    assert not thread.is_alive()
    assert g._ws_manager is None
    assert g._stream_callbacks == []
    assert not g.is_streaming()


@pytest.mark.asyncio
async def test_manager_subscribe_pairs_preserves_exchange():
    """subscribe_pairs must not hardcode NSE (unlike legacy subscribe())."""
    mgr = DhanWebSocketManager(access_token="t", client_id="c")
    await mgr.subscribe_pairs([("RELIANCE", "NSE"), ("GOLD", "MCX")])
    assert ("GOLD", "MCX") in mgr._subscriptions
    assert ("RELIANCE", "NSE") in mgr._subscriptions
