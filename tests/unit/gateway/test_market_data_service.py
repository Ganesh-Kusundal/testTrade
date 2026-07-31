from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.contracts import MarketDepth, Quote
from scalpr.domain.instrument import (
    Exchange,
    MarketFeed,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)
from scalpr.domain.tick import OHLC, Candle
from scalpr.gateway.market_data_service import MarketDataService
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
        freeze_quantity=None,
        expiry=None,
        strike=None,
        option_type=None,
    )


class TestMarketDataServiceQuote:
    def test_quote_returns_domain_quote(self):
        client = MagicMock(spec=DhanClient)
        client.get_quote.return_value = Quote(
            symbol="TCS", exchange="NSE", ltp=Decimal("100.00"),
            open=Decimal("99"), high=Decimal("101"), low=Decimal("98"),
            close=Decimal("99.5"), volume=1000,
        )
        svc = MarketDataService(client)
        resolved = make_resolved()
        result = svc.quote(resolved)
        assert isinstance(result, Quote)
        assert result.ltp == Decimal("100.00")
        client.get_quote.assert_called_once_with(resolved)

    def test_ohlc_returns_ohlc_from_quote(self):
        client = MagicMock(spec=DhanClient)
        client.get_quote.return_value = Quote(
            symbol="TCS", exchange="NSE", ltp=Decimal("100.00"),
            open=Decimal("99"), high=Decimal("101"), low=Decimal("98"),
            close=Decimal("99.5"), volume=1000,
        )
        svc = MarketDataService(client)
        resolved = make_resolved()
        result = svc.ohlc(resolved)
        assert isinstance(result, OHLC)
        assert result.open == Decimal("99")
        assert result.high == Decimal("101")
        assert result.low == Decimal("98")
        assert result.close == Decimal("99.5")


class TestMarketDataServiceDepth:
    def test_depth_returns_market_depth(self):
        client = MagicMock(spec=DhanClient)
        from scalpr.domain.contracts import DepthLevel
        from scalpr.domain.contracts import MarketDepth as ContractsMarketDepth
        client.get_market_depth.return_value = ContractsMarketDepth(
            symbol="TCS", exchange="NSE",
            bid_levels=[DepthLevel(price=Decimal("99.95"), quantity=100, orders=5)],
            ask_levels=[DepthLevel(price=Decimal("100.05"), quantity=50, orders=3)],
            timestamp=None,
        )
        svc = MarketDataService(client)
        resolved = make_resolved()
        result = svc.depth(resolved, levels=5)
        assert isinstance(result, MarketDepth)
        assert len(result.bid_levels) == 1
        assert result.bid_levels[0].price == Decimal("99.95")


class TestMarketDataServiceHistorical:
    def test_historical_returns_candles(self):
        client = MagicMock(spec=DhanClient)
        client.get_historical.return_value = [
            {"timestamp": 1719436800, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000, "oi": 500},
        ]
        svc = MarketDataService(client)
        resolved = make_resolved()
        result = svc.historical(resolved, interval="1D", start=datetime(2024, 6, 25), end=datetime(2024, 6, 25))
        assert len(result) == 1
        assert isinstance(result[0], Candle)
        assert result[0].open == Decimal("100.0")
        assert result[0].close == Decimal("100.5")
        assert result[0].volume == 1000
        assert result[0].open_interest == 500


class TestMarketDataServiceSubscribe:
    def test_subscribe_feed_returns_subscription(self):
        client = MagicMock(spec=DhanClient)
        svc = MarketDataService(client)
        resolved = make_resolved()
        sub = svc.subscribe_feed(MarketFeed.QUOTE, [resolved], on_event=lambda e: None)
        assert isinstance(sub, Subscription)
        assert sub.mode == MarketFeed.QUOTE
        assert sub.is_active is True

    def test_subscribe_feed_batches_100(self):
        client = MagicMock(spec=DhanClient)
        svc = MarketDataService(client)
        resolved = make_resolved()
        instruments = [resolved] * 150
        sub = svc.subscribe_feed(MarketFeed.TICKER, instruments, on_event=lambda e: None)
        assert isinstance(sub, Subscription)
        assert len(sub.instruments) == 150
        # Each instrument should have subscribe_quotes called
        assert client.subscribe_quotes.call_count == 150

    def test_unsubscribe_deactivates(self):
        client = MagicMock(spec=DhanClient)
        svc = MarketDataService(client)
        resolved = make_resolved()
        sub = svc.subscribe_feed(MarketFeed.QUOTE, [resolved], on_event=lambda e: None)
        svc.unsubscribe(sub)
        assert sub.is_active is False

    def test_unsubscribe_idempotent(self):
        client = MagicMock(spec=DhanClient)
        svc = MarketDataService(client)
        resolved = make_resolved()
        sub = svc.subscribe_feed(MarketFeed.QUOTE, [resolved], on_event=lambda e: None)
        svc.unsubscribe(sub)
        svc.unsubscribe(sub)  # should not raise
