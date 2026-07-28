"""Tests for OptionChainAdapter — payload contract verified against live Dhan v2.

Live verification (2026-07-27): POST /optionchain/expirylist and /optionchain
require ``UnderlyingScrip`` / ``UnderlyingSeg`` keys; ``securityId`` /
``exchangeSegment`` return HTTP 400 "Invalid SecurityId". Per-leg data carries
``security_id`` but NO ``trading_symbol``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.brokers.dhan.option_chain import OptionChainAdapter

# Shape captured from a live /optionchain response (NIFTY 2026-07-28)
LIVE_CHAIN_RESPONSE = {
    "data": {
        "last_price": 23986.45,
        "oc": {
            "23800.000000": {
                "ce": {
                    "last_price": 160.75,
                    "oi": 1596335,
                    "volume": 40429090,
                    "top_bid_price": 160.75,
                    "top_ask_price": 161,
                    "security_id": 49081,
                    "greeks": {"delta": 0.62, "theta": 0, "gamma": 0, "vega": 0},
                },
                "pe": {
                    "last_price": 12.4,
                    "oi": 2001000,
                    "volume": 51000000,
                    "top_bid_price": 12.35,
                    "top_ask_price": 12.45,
                    "security_id": 49082,
                    "greeks": {"delta": -0.38, "theta": 0, "gamma": 0, "vega": 0},
                },
            },
        },
    },
    "status": "success",
}


def _adapter():
    client = MagicMock()
    resolver = MagicMock()
    resolved = MagicMock()
    resolved.security_id = 13
    resolved.dhan_exchange_segment = "IDX_I"
    resolver.resolve_full.return_value = resolved
    return OptionChainAdapter(client, resolver), client, resolver


class TestOptionChainPayloadContract:
    def test_expirylist_uses_underlying_scrip_keys(self):
        adapter, client, _ = _adapter()
        client.post.side_effect = [
            {"data": ["2026-07-28", "2026-08-04"]},
            LIVE_CHAIN_RESPONSE,
        ]
        adapter.get_option_chain("NIFTY", "NSE")
        expiry_call = client.post.call_args_list[0]
        assert expiry_call.args[0] == "/optionchain/expirylist"
        assert expiry_call.kwargs["json"] == {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I",
        }

    def test_chain_uses_underlying_scrip_keys(self):
        adapter, client, _ = _adapter()
        client.post.return_value = LIVE_CHAIN_RESPONSE
        adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))
        chain_call = client.post.call_args_list[0]
        assert chain_call.args[0] == "/optionchain"
        assert chain_call.kwargs["json"] == {
            "UnderlyingScrip": 13,
            "UnderlyingSeg": "IDX_I",
            "Expiry": "2026-07-28",
        }

    def test_underlying_resolved_via_resolve_full(self):
        adapter, client, resolver = _adapter()
        client.post.return_value = LIVE_CHAIN_RESPONSE
        adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))
        resolver.resolve_full.assert_called_once_with("NIFTY", "NSE")


class TestFlattenChain:
    def test_flatten_live_shape(self):
        adapter, client, _ = _adapter()
        client.post.return_value = LIVE_CHAIN_RESPONSE
        chain = adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))
        assert len(chain) == 2  # CE + PE
        ce = next(c for c in chain if c["security_id"] == 49081)
        assert ce["strike"] == Decimal("23800.000000")
        assert ce["bid"] == Decimal("160.75")
        assert ce["ask"] == Decimal("161")
        assert ce["oi"] == 1596335
        assert ce["volume"] == 40429090
        assert ce["delta"] == 0.62

    def test_missing_trading_symbol_yields_empty_symbol(self):
        # Live responses carry no trading_symbol — symbol must default to ""
        adapter, client, _ = _adapter()
        client.post.return_value = LIVE_CHAIN_RESPONSE
        chain = adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))
        assert all(c["symbol"] == "" for c in chain)

    def test_malformed_security_id_normalises_to_none(self):
        # If Dhan ever returns a non-numeric security_id, the adapter must
        # coerce it to None (not crash) so the scanner's fallback path works.
        adapter, client, _ = _adapter()
        bad = {
            "data": {
                "oc": {
                    "23800.000000": {
                        "ce": {
                            "last_price": 160.75,
                            "oi": 100, "volume": 200,
                            "top_bid_price": 160, "top_ask_price": 161,
                            "security_id": "not-an-int",  # malformed
                            "greeks": {"delta": 0},
                        },
                    },
                },
            },
        }
        client.post.return_value = bad
        chain = adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))
        assert len(chain) == 1
        assert chain[0]["security_id"] is None

    def test_none_bid_ask_default_to_zero(self):
        # Defensive: Dhan may return None for top_bid_price/top_ask_price
        adapter, client, _ = _adapter()
        none_payload = {
            "data": {
                "oc": {
                    "23800.000000": {
                        "ce": {
                            "oi": 100, "volume": 200,
                            "top_bid_price": None, "top_ask_price": None,
                            "security_id": 49081,
                            "greeks": {"delta": None},
                        },
                    },
                },
            },
        }
        client.post.return_value = none_payload
        chain = adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))
        assert chain[0]["bid"] == Decimal("0")
        assert chain[0]["ask"] == Decimal("0")
        assert chain[0]["delta"] is None



class TestScannerAcceptsAdapterOutput:
    def test_scanner_resolves_by_security_id(self):
        # Live chain rows have security_id but no symbol — scanner must still
        # resolve them via resolver.get_by_security_id
        from scalpr.scanner.options_scanner import OptionsScanner

        adapter, client, _ = _adapter()
        client.post.return_value = LIVE_CHAIN_RESPONSE
        chain = adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))

        resolver = MagicMock()
        inst = MagicMock()
        resolver.get_by_security_id.return_value = inst
        scanner = OptionsScanner(resolver, min_oi=1, min_volume=1, max_spread=Decimal("5"))

        picks = scanner.scan(Decimal("23800"), chain)
        assert picks == [inst, inst]  # CE + PE, both ATM and liquid
        resolver.get_by_security_id.assert_any_call(49081)
        resolver.get_by_security_id.assert_any_call(49082)
        resolver.resolve.assert_not_called()  # no empty-symbol resolve attempts
