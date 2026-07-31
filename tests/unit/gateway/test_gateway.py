from __future__ import annotations

from unittest.mock import MagicMock

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.instrument import (
    Exchange,
    MarketFeed,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)
from scalpr.engine.clock import StaticClock
from scalpr.engine.message_bus import RecordingBus
from scalpr.gateway import Gateway
from scalpr.gateway.instrument import Instrument
from scalpr.gateway.subscription import Subscription


def make_resolved(symbol: str = "TCS") -> ResolvedInstrument:
    return ResolvedInstrument(
        instrument_id=SimpleInstrumentId(symbol=symbol, exchange=Exchange.NSE),
        security_id="112833",
        exchange=Exchange.NSE,
        segment=Segment.EQUITY,
        trading_symbol=symbol,
        wire_segment="NSE_EQ",
        lot_size=1,
        tick_size=Decimal("0.05"),
        freeze_quantity=100,
        expiry=None,
        strike=None,
        option_type=None,
    )


from decimal import Decimal


class TestGateway:
    def test_gateway_construction(self):
        client = MagicMock(spec=DhanClient)
        client.broker = "dhan"
        bus = RecordingBus()
        clock = StaticClock()
        gw = Gateway(client=client, bus=bus, clock=clock)
        assert gw.orders is not None
        assert gw.portfolio is not None
        assert gw.account is not None
        assert gw.trader_control is not None
        assert gw.order_updates is not None

    def test_instrument_returns_instrument(self):
        client = MagicMock(spec=DhanClient)
        client.broker = "dhan"
        client.resolve_instrument.return_value = make_resolved("TCS")
        bus = RecordingBus()
        gw = Gateway(client=client, bus=bus, clock=StaticClock())
        inst = gw.instrument("TCS:NSE")
        assert isinstance(inst, Instrument)
        assert inst.resolved.trading_symbol == "TCS"

    def test_subscribe_feed_returns_subscription(self):
        client = MagicMock(spec=DhanClient)
        client.broker = "dhan"
        client.resolve_instrument.return_value = make_resolved("TCS")
        bus = RecordingBus()
        gw = Gateway(client=client, bus=bus, clock=StaticClock())
        sub = gw.subscribe_feed(MarketFeed.TICKER, ["TCS:NSE"], on_event=lambda e: None)
        assert isinstance(sub, Subscription)
        assert sub.is_active is True

    def test_unsubscribe_deactivates(self):
        client = MagicMock(spec=DhanClient)
        client.broker = "dhan"
        client.resolve_instrument.return_value = make_resolved("TCS")
        bus = RecordingBus()
        gw = Gateway(client=client, bus=bus, clock=StaticClock())
        sub = gw.subscribe_feed(MarketFeed.QUOTE, ["TCS:NSE"], on_event=lambda e: None)
        gw.unsubscribe(sub)
        assert sub.is_active is False

    def test_start_and_stop(self):
        client = MagicMock(spec=DhanClient)
        client.broker = "dhan"
        bus = RecordingBus()
        gw = Gateway(client=client, bus=bus, clock=StaticClock())
        gw.start()
        client.start.assert_called_once()
        assert gw._started is True
        gw.stop()
        client.stop.assert_called_once()
        assert gw._started is False

    def test_close_stops_gateway(self):
        client = MagicMock(spec=DhanClient)
        client.broker = "dhan"
        bus = RecordingBus()
        gw = Gateway(client=client, bus=bus, clock=StaticClock())
        gw.start()
        gw.close()
        assert gw._started is False
