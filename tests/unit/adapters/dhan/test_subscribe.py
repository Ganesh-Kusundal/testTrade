from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.instrument import Exchange, ResolvedInstrument, Segment, SimpleInstrumentId
from scalpr.engine.clock import StaticClock
from scalpr.engine.message_bus import RecordingBus


class TestDhanClientSubscribeHighLevel(unittest.TestCase):
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

        self.mock_ws = self.mocks[3].return_value
        self.mock_resolver = self.mocks[4].return_value
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

        self.client = DhanClient(self.bus, self.clock, self.config)

    # ── subscribe — quote ─────────────────────────────────────────────

    def test_subscribe_quote_resolves_and_subscribes(self):
        self.client.subscribe("RELIANCE", "NSE", type="quote")
        self.mock_resolver.resolve_full.assert_called_with("RELIANCE", "NSE")
        self.mock_ws.subscribe.assert_called_with([("12345", "NSE_EQ")], mode="quote")

    def test_subscribe_quote_default_exchange_nse(self):
        self.client.subscribe("RELIANCE")
        self.mock_resolver.resolve_full.assert_called_with("RELIANCE", "NSE")

    def test_subscribe_quote_bse_exchange(self):
        self.mock_resolver.resolve_full.return_value = ResolvedInstrument(
            instrument_id=SimpleInstrumentId(symbol="RELIANCE", exchange=Exchange.BSE),
            security_id="67890",
            exchange=Exchange.BSE,
            segment=Segment.EQUITY,
            trading_symbol="RELIANCE",
            wire_segment="BSE_EQ",
            lot_size=1,
            tick_size=Decimal("0.05"),
            freeze_quantity=None,
            expiry=None,
            strike=None,
            option_type=None,
        )
        self.client.subscribe("RELIANCE", "BSE", type="quote")
        self.mock_resolver.resolve_full.assert_called_with("RELIANCE", "BSE")
        self.mock_ws.subscribe.assert_called_with([("67890", "BSE_EQ")], mode="quote")

    def test_subscribe_quote_mcx_exchange(self):
        self.mock_resolver.resolve_full.return_value = ResolvedInstrument(
            instrument_id=SimpleInstrumentId(symbol="CRUDEOIL", exchange=Exchange.MCX),
            security_id="99999",
            exchange=Exchange.MCX,
            segment=Segment.COMMODITY,
            trading_symbol="CRUDEOIL",
            wire_segment="MCX_COMM",
            lot_size=1,
            tick_size=Decimal("0.05"),
            freeze_quantity=None,
            expiry=None,
            strike=None,
            option_type=None,
        )
        self.client.subscribe("CRUDEOIL", "MCX", type="quote")
        self.mock_resolver.resolve_full.assert_called_with("CRUDEOIL", "MCX")
        self.mock_ws.subscribe.assert_called_with([("99999", "MCX_COMM")], mode="quote")

    def test_subscribe_unknown_exchange_defaults_nse(self):
        self.client.subscribe("RELIANCE", exchange="INVALID", type="quote")
        self.mock_resolver.resolve_full.assert_called_with("RELIANCE", "NSE")

    def test_subscribe_quote_nse_fno_exchange(self):
        self.mock_resolver.resolve_full.return_value = ResolvedInstrument(
            instrument_id=SimpleInstrumentId(symbol="BANKNIFTY", exchange=Exchange.NSE),
            security_id="55555",
            exchange=Exchange.NSE,
            segment=Segment.FUTURES,
            trading_symbol="BANKNIFTY",
            wire_segment="NSE_FNO",
            lot_size=15,
            tick_size=Decimal("0.05"),
            freeze_quantity=None,
            expiry=datetime(2024, 7, 25).date(),
            strike=None,
            option_type=None,
        )
        self.client.subscribe("BANKNIFTY", "NSE", type="quote")
        self.mock_resolver.resolve_full.assert_called_with("BANKNIFTY", "NSE")
        self.mock_ws.subscribe.assert_called_with([("55555", "NSE_FNO")], mode="quote")

    # ── subscribe — depth ────────────────────────────────────────────

    def test_subscribe_depth_20_resolves_and_subscribes(self):
        self.client.subscribe("RELIANCE", "NSE", type="depth", level=20)
        self.mock_resolver.resolve_full.assert_called_with("RELIANCE", "NSE")
        self.mock_ws.subscribe_depth.assert_called_with([("12345", "NSE_EQ")], level=20)

    def test_subscribe_depth_200_resolves_and_subscribes(self):
        self.client.subscribe("RELIANCE", "NSE", type="depth", level=200)
        self.mock_resolver.resolve_full.assert_called_with("RELIANCE", "NSE")
        self.mock_ws.subscribe_depth.assert_called_with([("12345", "NSE_EQ")], level=200)

    def test_subscribe_depth_default_level_20(self):
        self.client.subscribe("RELIANCE", "NSE", type="depth")
        self.mock_ws.subscribe_depth.assert_called_with([("12345", "NSE_EQ")], level=20)

    # ── subscribe — errors ───────────────────────────────────────────

    def test_subscribe_invalid_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            self.client.subscribe("RELIANCE", type="invalid")
        self.assertIn("invalid", str(ctx.exception))

    def test_subscribe_invalid_depth_level_raises(self):
        self.mock_ws.subscribe_depth.side_effect = ValueError("Depth level must be 20 or 200, got 999")
        with self.assertRaises(ValueError):
            self.client.subscribe("RELIANCE", type="depth", level=999)

    # ── unsubscribe ──────────────────────────────────────────────────

    def test_unsubscribe_quote(self):
        self.client.unsubscribe("RELIANCE", "NSE", type="quote")
        self.mock_resolver.resolve_full.assert_called_with("RELIANCE", "NSE")
        self.mock_ws.unsubscribe.assert_called_with([("12345", "NSE_EQ")])

    def test_unsubscribe_depth(self):
        self.client.unsubscribe("RELIANCE", "NSE", type="depth")
        self.mock_resolver.resolve_full.assert_called_with("RELIANCE", "NSE")
        self.mock_ws.unsubscribe_depth.assert_called_with([("12345", "NSE_EQ")], level=20)

    def test_unsubscribe_invalid_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            self.client.unsubscribe("RELIANCE", type="invalid")
        self.assertIn("invalid", str(ctx.exception))

    def test_unsubscribe_twice_no_error(self):
        self.client.unsubscribe("RELIANCE", type="quote")
        self.client.unsubscribe("RELIANCE", type="quote")

    # ── subscribe_batch ──────────────────────────────────────────────

    def test_subscribe_batch_empty(self):
        self.client.subscribe_batch([])
        self.mock_ws.subscribe.assert_not_called()
        self.mock_ws.subscribe_depth.assert_not_called()

    def test_subscribe_batch_single_quote(self):
        self.client.subscribe_batch([("RELIANCE", "NSE", "quote", None)])
        self.mock_ws.subscribe.assert_called_once()

    def test_subscribe_batch_single_depth(self):
        self.client.subscribe_batch([("RELIANCE", "NSE", "depth", 20)])
        self.mock_ws.subscribe_depth.assert_called_once()

    def test_subscribe_batch_mixed_types(self):
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
        specs = [
            ("RELIANCE", "NSE", "quote", None),
            ("RELIANCE", "NSE", "depth", 200),
        ]
        self.client.subscribe_batch(specs)
        self.mock_ws.subscribe.assert_called_once_with([("12345", "NSE_EQ")], mode="quote")
        self.mock_ws.subscribe_depth.assert_called_once_with([("12345", "NSE_EQ")], level=200)

    def test_subscribe_batch_defaults_level_to_20(self):
        self.client.subscribe_batch([("RELIANCE", "NSE", "depth", None)])
        self.mock_ws.subscribe_depth.assert_called_with([("12345", "NSE_EQ")], level=20)

    def test_subscribe_batch_multiple_symbols(self):
        self.mock_resolver.resolve_full.side_effect = [
            ResolvedInstrument(
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
            ),
            ResolvedInstrument(
                instrument_id=SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE),
                security_id="67890",
                exchange=Exchange.NSE,
                segment=Segment.EQUITY,
                trading_symbol="TCS",
                wire_segment="NSE_EQ",
                lot_size=1,
                tick_size=Decimal("0.05"),
                freeze_quantity=None,
                expiry=None,
                strike=None,
                option_type=None,
            ),
        ]
        specs = [
            ("RELIANCE", "NSE", "quote", None),
            ("TCS", "NSE", "quote", None),
        ]
        self.client.subscribe_batch(specs)
        self.assertEqual(self.mock_ws.subscribe.call_count, 2)

    # ── subscription_status ──────────────────────────────────────────

    def test_subscription_status_returns_counts(self):
        self.mock_ws.subscription_count = 5
        self.mock_ws.subscription_capacity_remaining = 995
        self.mock_ws.depth_subscription_count_20 = 3
        self.mock_ws.depth_capacity_remaining_20 = 97
        self.mock_ws.depth_subscription_count_200 = 1
        self.mock_ws.depth_capacity_remaining_200 = 49

        status = self.client.subscription_status()

        self.assertEqual(status["quote"]["count"], 5)
        self.assertEqual(status["quote"]["capacity"], 995)
        self.assertEqual(status["depth_20"]["count"], 3)
        self.assertEqual(status["depth_20"]["capacity"], 97)
        self.assertEqual(status["depth_200"]["count"], 1)
        self.assertEqual(status["depth_200"]["capacity"], 49)

    def test_subscription_status_defaults_zero(self):
        self.mock_ws.subscription_count = 0
        self.mock_ws.subscription_capacity_remaining = 1000
        self.mock_ws.depth_subscription_count_20 = 0
        self.mock_ws.depth_capacity_remaining_20 = 100
        self.mock_ws.depth_subscription_count_200 = 0
        self.mock_ws.depth_capacity_remaining_200 = 50

        status = self.client.subscription_status()
        self.assertEqual(status, {
            "quote": {"count": 0, "capacity": 1000},
            "depth_20": {"count": 0, "capacity": 100},
            "depth_200": {"count": 0, "capacity": 50},
        })


if __name__ == "__main__":
    unittest.main()
