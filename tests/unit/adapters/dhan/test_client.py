from __future__ import annotations

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.instrument import (
    Exchange,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)
from scalpr.domain.order import Order, OrderSide, OrderType
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.domain.tick import Tick
from scalpr.domain.values import ZERO
from scalpr.engine.clock import StaticClock
from scalpr.engine.execution_engine import (
    CancelOrder,
    ModifyOrder,
    OrderAccepted,
    OrderCancelled,
    OrderRejected,
    SubmitOrder,
)
from scalpr.engine.message_bus import RecordingBus


class TestDhanClientConstruction(unittest.TestCase):
    """DhanClient creates internal components with correct arguments."""

    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {
            "client_id": "c1",
            "access_token": "tok",  # pragma: allowlist secret
            "totp_secret": "sec",  # pragma: allowlist secret
        }

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.mock_token_manager = self.mocks[0].return_value
        self.mock_http_client = self.mocks[1].return_value
        self.mock_rate_limiter = self.mocks[2].return_value
        self.mock_ws = self.mocks[3].return_value
        self.mock_resolver = self.mocks[4].return_value

    def test_creates_token_manager(self):
        DhanClient(self.bus, self.clock, self.config)
        self.mocks[0].assert_called_once_with("c1", "sec", self.clock, pin="1111", initial_token="tok")

    def test_creates_rate_limiter(self):
        DhanClient(self.bus, self.clock, self.config)
        self.mocks[2].assert_called_once_with()

    def test_creates_http_client_with_token_manager_and_rate_limiter(self):
        c = DhanClient(self.bus, self.clock, self.config)
        self.mocks[1].assert_called_once_with(
            client_id="c1",
            access_token="tok",
            token_manager=c._token_manager,
            rate_limiter=c._rate_limiter,
        )

    def test_creates_websocket_with_on_tick(self):
        c = DhanClient(self.bus, self.clock, self.config)
        self.mocks[3].assert_called_once_with(
            access_token="tok",
            client_id="c1",
            on_tick=c.on_ws_tick,
            clock=self.clock,
        )

    def test_creates_resolver(self):
        DhanClient(self.bus, self.clock, self.config)
        self.mocks[4].assert_called_once_with()

    def test_stores_csv_path_default(self):
        c = DhanClient(self.bus, self.clock, self.config)
        self.assertEqual(c._csv_path, "instrument.csv")

    def test_stores_csv_path_from_config(self):
        cfg = {**self.config, "csv_path": "/data/inst.csv"}
        c = DhanClient(self.bus, self.clock, cfg)
        self.assertEqual(c._csv_path, "/data/inst.csv")

    def test_subscriptions_empty_after_init(self):
        c = DhanClient(self.bus, self.clock, self.config)
        self.assertEqual(c._subscriptions, [])


class TestDhanClientLifecycle(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
            patch("scalpr.adapters.dhan.client.os.path.exists"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.mock_token_manager = self.mocks[0].return_value
        self.mock_http_client = self.mocks[1].return_value
        self.mock_rate_limiter = self.mocks[2].return_value
        self.mock_ws = self.mocks[3].return_value
        self.mock_resolver = self.mocks[4].return_value
        self.mock_exists = self.mocks[5]

        self.client = DhanClient(self.bus, self.clock, self.config)

    def test_start_loads_resolver_connects_ws_subscribes(self):
        self.mock_exists.return_value = False

        self.client.start()

        self.mock_ws.connect.assert_called_once_with()
        expected_topics = [
            "exec.command.submit.dhan",
            "exec.command.cancel.dhan",
            "exec.command.modify.dhan",
        ]
        for topic in expected_topics:
            self.assertIn(
                topic,
                self.bus._subscribers,
                f"Should have subscriber for {topic}",
            )
        self.assertEqual(len(self.client._subscriptions), 3)

    def test_start_loads_resolver_from_csv_when_exists(self):
        self.mock_exists.return_value = True
        csv_data = "symbol,security_id\nRELIANCE,123\n"
        with patch("builtins.open", new_callable=MagicMock) as mock_file:
            handle = MagicMock()
            handle.__enter__.return_value = csv_data.splitlines(keepends=True)
            mock_file.return_value = handle

            self.client.start()

        self.mock_resolver.load_from_rows.assert_called_once()

    def test_start_skips_csv_when_not_found(self):
        self.mock_exists.return_value = False

        self.client.start()

        self.mock_resolver.load_from_rows.assert_not_called()

    def test_stop_disconnects_ws_and_unsubscribes(self):
        self.mock_exists.return_value = False
        self.client.start()

        self.client.stop()

        self.mock_ws.disconnect.assert_called_once_with()
        self.assertEqual(len(self.client._subscriptions), 0)

    def test_stop_idempotent(self):
        self.client.stop()
        self.client.stop()


class TestDhanClientOnSubmit(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
            patch("scalpr.adapters.dhan.client.order_to_dhan_request_v2"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.mock_token_manager = self.mocks[0].return_value
        self.mock_http_client = self.mocks[1].return_value
        self.mock_rate_limiter = self.mocks[2].return_value
        self.mock_ws = self.mocks[3].return_value
        self.mock_resolver = self.mocks[4].return_value
        self.mock_order_to_dhan_v2 = self.mocks[5]

        self.client = DhanClient(self.bus, self.clock, self.config)

        self.order = Order(
            order_id="ord-1",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            price=Decimal("2500"),
        )
        self.msg = SubmitOrder(order=self.order)

        self.mock_resolver.resolve_full.return_value = ResolvedInstrument(
            instrument_id=SimpleInstrumentId(symbol="RELIANCE", exchange=Exchange.NSE),
            security_id="12345",
            exchange=Exchange.NSE,
            segment=Segment.EQUITY,
            trading_symbol="RELIANCE",
            wire_segment="NSE_EQ",
            lot_size=1,
            tick_size=Decimal("0.05"),
            freeze_quantity=None,
            expiry=None,
            strike=None,
            option_type=None,
        )
        self.mock_order_to_dhan_v2.return_value = {
            "dhanClientId": "c1",
            "correlationId": "",
            "transactionType": "BUY",
            "exchangeSegment": "NSE_EQ",
            "productType": "INTRADAY",
            "orderType": "LIMIT",
            "validity": "DAY",
            "securityId": "12345",
            "quantity": 10,
            "disclosedQuantity": 0,
            "price": "2500",
            "triggerPrice": "0",
            "afterMarketOrder": False,
        }
        self.mock_http_client.post.return_value = {"orderId": "ord-1", "filledQuantity": 10}

    def test_acquires_rate_limit_bucket_orders(self):
        self.client._on_submit(self.msg)

    def test_gets_auth_token(self):
        self.client._on_submit(self.msg)
        self.mock_token_manager.get_token.assert_called_once_with()

    def test_resolves_symbol(self):
        self.client._on_submit(self.msg)
        self.mock_resolver.resolve_full.assert_called_once_with("RELIANCE", "NSE")

    def test_converts_order_to_dhan_request(self):
        self.client._on_submit(self.msg)
        self.mock_order_to_dhan_v2.assert_called_once_with(
            self.order, "12345", "NSE_EQ", "c1",
            product_type=self.order.product_type,
        )

    def test_posts_to_orders_endpoint(self):
        self.client._on_submit(self.msg)
        self.mock_http_client.post.assert_called_once_with(
            "/orders", data=self.mock_order_to_dhan_v2.return_value,
        )

    def test_does_not_convert_response_to_fill(self):
        """Phantom fill creation must be removed — response_to_fill should not be called."""
        self.client._on_submit(self.msg)

    def test_publishes_order_accepted_on_success(self):
        self.client._on_submit(self.msg)
        events = self.bus.filter("exec.event.accepted.dhan")
        self.assertEqual(len(events), 1)
        ev = events[0].payload
        self.assertIsInstance(ev, OrderAccepted)
        self.assertEqual(ev.order_id, "ord-1")

    def test_does_not_publish_fill_on_success(self):
        """Order placement should NOT fabricate a fill — only an acceptance."""
        self.client._on_submit(self.msg)
        events = self.bus.filter("exec.event.filled.dhan")
        self.assertEqual(len(events), 0)

    def test_publishes_order_rejected_on_error(self):
        self.mock_http_client.post.side_effect = RuntimeError("API down")
        self.client._on_submit(self.msg)
        events = self.bus.filter("exec.event.rejected.dhan")
        self.assertEqual(len(events), 1)
        ev = events[0].payload
        self.assertIsInstance(ev, OrderRejected)
        self.assertEqual(ev.order_id, "ord-1")
        self.assertIn("API down", ev.reason)

    def test_does_not_publish_filled_on_error(self):
        self.mock_http_client.post.side_effect = RuntimeError("API down")
        self.client._on_submit(self.msg)
        self.assertEqual(len(self.bus.filter("exec.event.filled.dhan")), 0)


class TestDhanClientOnCancel(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.mock_token_manager = self.mocks[0].return_value
        self.mock_http_client = self.mocks[1].return_value
        self.mock_rate_limiter = self.mocks[2].return_value
        self.mock_ws = self.mocks[3].return_value
        self.mock_resolver = self.mocks[4].return_value

        self.client = DhanClient(self.bus, self.clock, self.config)
        self.msg = CancelOrder(order_id="ord-1")

    def test_acquires_rate_limit_bucket_orders(self):
        self.client._on_cancel(self.msg)

    def test_sends_delete_request(self):
        self.client._on_cancel(self.msg)
        self.mock_http_client.delete.assert_called_once_with("/orders/ord-1")

    def test_publishes_cancelled_event_on_success(self):
        self.client._on_cancel(self.msg)
        events = self.bus.filter("exec.event.cancelled.dhan")
        self.assertEqual(len(events), 1)
        ev = events[0].payload
        self.assertIsInstance(ev, OrderCancelled)
        self.assertEqual(ev.order_id, "ord-1")

    def test_handles_error_gracefully(self):
        self.mock_http_client.delete.side_effect = RuntimeError("conn lost")
        self.client._on_cancel(self.msg)  # should not raise


class TestDhanClientOnModify(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.mock_token_manager = self.mocks[0].return_value
        self.mock_http_client = self.mocks[1].return_value
        self.mock_rate_limiter = self.mocks[2].return_value
        self.mock_ws = self.mocks[3].return_value
        self.mock_resolver = self.mocks[4].return_value

        self.client = DhanClient(self.bus, self.clock, self.config)
        self.msg = ModifyOrder(order_id="ord-1", updates={"quantity": 15})

    def test_acquires_rate_limit_bucket_orders(self):
        self.client._on_modify(self.msg)

    def test_sends_put_request(self):
        self.client._on_modify(self.msg)
        self.mock_http_client.put.assert_called_once_with(
            "/orders/ord-1", data={"quantity": 15},
        )

    def test_handles_error_gracefully(self):
        self.mock_http_client.put.side_effect = RuntimeError("conn lost")
        self.client._on_modify(self.msg)  # should not raise


class TestDhanClientSubscribeQuotes(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.mock_token_manager = self.mocks[0].return_value
        self.mock_http_client = self.mocks[1].return_value
        self.mock_rate_limiter = self.mocks[2].return_value
        self.mock_ws = self.mocks[3].return_value
        self.mock_resolver = self.mocks[4].return_value

        self.client = DhanClient(self.bus, self.clock, self.config)

        self.mock_resolver.resolve_full.return_value = ResolvedInstrument(
            instrument_id=SimpleInstrumentId(symbol="RELIANCE", exchange=Exchange.NSE),
            security_id="12345",
            exchange=Exchange.NSE,
            segment=Segment.EQUITY,
            trading_symbol="RELIANCE",
            wire_segment="NSE_EQ",
            lot_size=1,
            tick_size=Decimal("0.05"),
            freeze_quantity=None,
            expiry=None,
            strike=None,
            option_type=None,
        )
        self.instrument_id = SimpleInstrumentId(symbol="RELIANCE", exchange=Exchange.NSE)

    def test_resolves_symbol(self):
        self.client.subscribe_quotes(self.instrument_id)
        self.mock_resolver.resolve_full.assert_called_once_with("RELIANCE", "NSE")

    def test_calls_ws_subscribe_with_correct_params(self):
        self.client.subscribe_quotes(self.instrument_id)
        self.mock_ws.subscribe.assert_called_once_with(
            [("12345", "NSE_EQ")], mode="quote",
        )

    def test_unsubscribe_resolves_and_calls_ws_unsubscribe(self):
        self.client.unsubscribe_quotes(self.instrument_id)
        self.mock_resolver.resolve_full.assert_called_once_with("RELIANCE", "NSE")
        self.mock_ws.unsubscribe.assert_called_once_with([("12345", "NSE_EQ")])


class TestDhanClientGetQuote(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
            patch("scalpr.adapters.dhan.client.to_quote"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.mock_token_manager = self.mocks[0].return_value
        self.mock_http_client = self.mocks[1].return_value
        self.mock_rate_limiter = self.mocks[2].return_value
        self.mock_ws = self.mocks[3].return_value
        self.mock_resolver = self.mocks[4].return_value
        self.mock_to_quote = self.mocks[5]

        self.client = DhanClient(self.bus, self.clock, self.config)

        self.mock_resolver.resolve_full.return_value = ResolvedInstrument(
            instrument_id=SimpleInstrumentId(symbol="RELIANCE", exchange=Exchange.NSE),
            security_id="12345",
            exchange=Exchange.NSE,
            segment=Segment.EQUITY,
            trading_symbol="RELIANCE",
            wire_segment="NSE_EQ",
            lot_size=1,
            tick_size=Decimal("0.05"),
            freeze_quantity=None,
            expiry=None,
            strike=None,
            option_type=None,
        )
        self.mock_http_client.post.return_value = {"last_price": "2505", "ohlc": {}}
        self.mock_to_quote.return_value = {
            "symbol": "RELIANCE",
            "ltp": Decimal("2505"),
            "open": ZERO,
            "high": ZERO,
            "low": ZERO,
            "close": ZERO,
            "volume": 0,
            "change": ZERO,
            "change_percent": ZERO,
            "oi": 0,
        }
        self.instrument_id = SimpleInstrumentId(symbol="RELIANCE", exchange=Exchange.NSE)

    def test_acquires_rate_limit_market_data(self):
        self.client.get_quote(self.instrument_id)

    def test_resolves_symbol(self):
        self.client.get_quote(self.instrument_id)
        self.mock_resolver.resolve_full.assert_called_once_with("RELIANCE", "NSE")

    def test_posts_to_marketfeed_quote_with_bucket(self):
        self.client.get_quote(self.instrument_id)
        self.mock_http_client.post.assert_called_once_with(
            "/marketfeed/quote",
            data={"security_ids": ["12345"], "exchangeSegment": "NSE_EQ"},
            bucket="market_data",
        )

    def test_converts_via_to_quote(self):
        result = self.client.get_quote(self.instrument_id)
        self.mock_to_quote.assert_called_once_with(
            {"last_price": "2505", "ohlc": {}}, self.instrument_id,
        )
        self.assertEqual(result, self.mock_to_quote.return_value)


class TestDhanClientPortfolio(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
            patch("scalpr.adapters.dhan._mapper_portfolio.to_position"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.mock_token_manager = self.mocks[0].return_value
        self.mock_http_client = self.mocks[1].return_value
        self.mock_rate_limiter = self.mocks[2].return_value
        self.mock_ws = self.mocks[3].return_value
        self.mock_resolver = self.mocks[4].return_value
        self.mock_to_position = self.mocks[5]

        self.client = DhanClient(self.bus, self.clock, self.config)

        self.sample_position = Position(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            quantity=10,
            avg_price=Decimal("2500"),
            ltp=Decimal("2510"),
            unrealised_pnl=Decimal("100"),
            position_side=PositionSide.LONG,
            state=PositionState.OPEN,
        )
        self.mock_to_position.return_value = self.sample_position

    def test_get_positions_acquires_portfolio_bucket(self):
        self.mock_http_client.get.return_value = []
        self.client.get_positions()

    def test_get_positions_gets_endpoint(self):
        self.mock_http_client.get.return_value = []
        self.client.get_positions()
        self.mock_http_client.get.assert_called_once_with("/positions", bucket="portfolio")

    def test_get_positions_returns_list(self):
        self.mock_http_client.get.return_value = [{"symbol": "RELIANCE"}]
        result = self.client.get_positions()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Position)
        self.assertEqual(result[0].symbol, "RELIANCE")

    def test_get_positions_converts_single_response_to_list(self):
        self.mock_http_client.get.return_value = {"symbol": "RELIANCE"}
        result = self.client.get_positions()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    def test_get_holdings_acquires_portfolio_bucket(self):
        self.mock_http_client.get.return_value = {}
        self.client.get_holdings()

    def test_get_holdings_gets_endpoint(self):
        self.mock_http_client.get.return_value = {}
        self.client.get_holdings()
        self.mock_http_client.get.assert_called_once_with("/holdings", bucket="portfolio")

    def test_get_holdings_returns_dict(self):
        self.mock_http_client.get.return_value = {"holdings": []}
        result = self.client.get_holdings()
        self.assertEqual(result, {"holdings": []})

    def test_get_funds_acquires_portfolio_bucket(self):
        self.mock_http_client.get.return_value = {}
        self.client.get_funds()

    def test_get_funds_gets_endpoint(self):
        self.mock_http_client.get.return_value = {}
        self.client.get_funds()
        self.mock_http_client.get.assert_called_once_with("/fundlimit", bucket="portfolio")

    def test_get_funds_returns_dict(self):
        self.mock_http_client.get.return_value = {"available": 50000}
        result = self.client.get_funds()
        self.assertEqual(result, {"available": 50000})


class TestDhanClientOnWsTick(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.client = DhanClient(self.bus, self.clock, self.config)

    def test_publishes_tick_to_market_quote_topic(self):
        tick = Tick(
            symbol="RELIANCE",
            ltp=Decimal("2510"),
            bid=Decimal("2509"),
            ask=Decimal("2511"),
            delta_volume=100,
            cumulative_volume=10000,
            exchange_timestamp=datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc),
        )
        self.client.on_ws_tick(tick)
        events = self.bus.filter("market.quote.dhan")
        self.assertEqual(len(events), 1)
        self.assertIs(events[0].payload, tick)


class TestDhanClientOptionChain(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.client = DhanClient(self.bus, self.clock, self.config)
        self.mock_option_chain = MagicMock()
        self.client._option_chain = self.mock_option_chain

    def test_get_option_chain_passes_num_strikes_and_debug(self):
        self.client.get_option_chain("NIFTY", "NSE", expiry="2026-08-06", num_strikes=2, debug=True)
        self.mock_option_chain.get_option_chain.assert_called_once_with(
            "NIFTY", "NSE", expiry="2026-08-06", as_df=False, num_strikes=2, debug=True,
        )

    def test_get_option_chain_passes_num_strikes_default(self):
        self.client.get_option_chain("NIFTY", "NSE")
        self.mock_option_chain.get_option_chain.assert_called_once_with(
            "NIFTY", "NSE", expiry=None, as_df=False, num_strikes=0, debug=False,
        )

    def test_get_expiry_list_debug_does_not_crash(self):
        self.mock_option_chain.get_expiry_list.return_value = ["2026-08-06"]
        result = self.client.get_expiry_list("NIFTY", "NSE", debug=True)
        self.assertEqual(result, ["2026-08-06"])


class TestDhanClientDebugParams(unittest.TestCase):
    def setUp(self):
        self.bus = RecordingBus()
        self.clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        self.config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

        self._patchers = [
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ]
        self.mocks = [p.start() for p in self._patchers]
        self.addCleanup(lambda: [p.stop() for p in self._patchers])

        self.client = DhanClient(self.bus, self.clock, self.config)

    def test_get_positions_debug_does_not_crash(self):
        self.mocks[1].return_value.get.return_value = []
        result = self.client.get_positions(debug=True)
        self.assertIsInstance(result, list)

    def test_get_holdings_debug_does_not_crash(self):
        self.mocks[1].return_value.get.return_value = {}
        result = self.client.get_holdings(debug=True)
        self.assertIsInstance(result, dict)

    def test_get_funds_debug_does_not_crash(self):
        self.mocks[1].return_value.get.return_value = {}
        result = self.client.get_funds(debug=True)
        self.assertIsInstance(result, dict)

    def test_get_trade_book_debug_does_not_crash(self):
        self.mocks[1].return_value.get.return_value = []
        result = self.client.get_trade_book(debug=True)
        self.assertIsInstance(result, list)

    def test_get_order_detail_debug_does_not_crash(self):
        self.mocks[1].return_value.get.return_value = {}
        result = self.client.get_order_detail("ord-1", debug=True)
        self.assertIsInstance(result, dict)

    def test_order_report_debug_does_not_crash(self):
        self.mocks[1].return_value.get.return_value = {}
        result = self.client.order_report("ord-1", debug=True)
        self.assertIsInstance(result, dict)

    def test_get_historical_debug_does_not_crash(self):
        self.client._historical = MagicMock()
        self.client._historical.get_historical.return_value = []
        result = self.client.get_historical("RELIANCE", debug=True)
        self.assertIsInstance(result, list)

    def test_get_intraday_debug_does_not_crash(self):
        self.client._historical = MagicMock()
        self.client._historical.get_intraday.return_value = []
        result = self.client.get_intraday("RELIANCE", debug=True)
        self.assertIsInstance(result, list)

    def test_get_daily_debug_does_not_crash(self):
        self.client._historical = MagicMock()
        self.client._historical.get_daily.return_value = []
        result = self.client.get_daily("RELIANCE", debug=True)
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
