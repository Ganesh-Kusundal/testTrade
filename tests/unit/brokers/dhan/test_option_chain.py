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

import pytest

from scalpr.brokers.dhan.http_client import DhanHttpClient
from scalpr.brokers.dhan.option_chain import OptionChainAdapter
from scalpr.brokers.dhan.resolution import SymbolResolver
from scalpr.brokers.errors import OptionChainNotSupported

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


def _row(**overrides) -> dict:
    base = {
        "SEM_EXM_EXCH_ID": "NSE",
        "SEM_SEGMENT": "E",
        "SEM_SMST_SECURITY_ID": "2885",
        "SEM_INSTRUMENT_NAME": "EQUITY",
        "SEM_TRADING_SYMBOL": "RELIANCE",
        "SEM_LOT_UNITS": 1,
        "SEM_TICK_SIZE": 0.05,
        "SEM_EXPIRY_DATE": None,
        "SEM_STRIKE_PRICE": None,
        "SEM_OPTION_TYPE": None,
        "SEM_CUSTOM_SYMBOL": None,
        "SM_SYMBOL_NAME": None,
    }
    base.update(overrides)
    return base


def _resolver(include_options=False):
    """Real SymbolResolver populated with test instruments.

    Args:
        include_options: If True, load NIFTY option contracts at security_ids
            49081/49082 so ``get_by_security_id`` returns real Instruments.
    """
    rows = [
        _row(SEM_TRADING_SYMBOL="NIFTY", SEM_SMST_SECURITY_ID="13",
             SEM_SEGMENT="I", SEM_INSTRUMENT_NAME="INDEX"),
        _row(SEM_TRADING_SYMBOL="TCS", SEM_SMST_SECURITY_ID="2885"),
        _row(SEM_TRADING_SYMBOL="RELIANCE", SEM_SMST_SECURITY_ID="5000",
             SEM_EXM_EXCH_ID="BSE"),
        _row(SEM_TRADING_SYMBOL="GOLD-01Aug2026-FUT", SEM_SMST_SECURITY_ID="12345",
             SEM_EXM_EXCH_ID="MCX", SEM_SEGMENT="M",
             SEM_INSTRUMENT_NAME="FUTCOM",
             SEM_EXPIRY_DATE="2026-08-01", SM_SYMBOL_NAME="GOLD"),
        _row(SEM_TRADING_SYMBOL="SILVER-30Jul2026-FUT", SEM_SMST_SECURITY_ID="471725",
             SEM_EXM_EXCH_ID="MCX", SEM_SEGMENT="M",
             SEM_INSTRUMENT_NAME="FUTCOM",
             SEM_EXPIRY_DATE="2026-07-30", SM_SYMBOL_NAME="SILVER"),
    ]
    if include_options:
        rows.extend([
            _row(SEM_TRADING_SYMBOL="NIFTY 28JUL26 23800 CE", SEM_SMST_SECURITY_ID="49081",
                 SEM_SEGMENT="D", SEM_INSTRUMENT_NAME="OPTIDX",
                 SEM_LOT_UNITS=25,
                 SEM_EXPIRY_DATE="2026-07-28", SEM_STRIKE_PRICE=23800.0,
                 SEM_OPTION_TYPE="CE", SM_SYMBOL_NAME="NIFTY"),
            _row(SEM_TRADING_SYMBOL="NIFTY 28JUL26 23800 PE", SEM_SMST_SECURITY_ID="49082",
                 SEM_SEGMENT="D", SEM_INSTRUMENT_NAME="OPTIDX",
                 SEM_LOT_UNITS=25,
                 SEM_EXPIRY_DATE="2026-07-28", SEM_STRIKE_PRICE=23800.0,
                 SEM_OPTION_TYPE="PE", SM_SYMBOL_NAME="NIFTY"),
        ])
    r = SymbolResolver()
    r.load_from_rows(rows)
    return r


def _adapter(**resolver_kwargs):
    client = MagicMock(spec=DhanHttpClient)
    resolver = _resolver(**resolver_kwargs)
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
        adapter, client, _ = _adapter()
        client.post.return_value = LIVE_CHAIN_RESPONSE
        adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))
        payload = client.post.call_args_list[0].kwargs["json"]
        assert payload["UnderlyingScrip"] == 13
        assert payload["UnderlyingSeg"] == "IDX_I"


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

    def test_symbol_backfilled_from_resolver(self):
        # Live responses carry no trading_symbol; the flat form must backfill
        # it from the resolver by security_id so callers can resolve the leg.
        adapter, client, _ = _adapter(include_options=True)
        client.post.return_value = LIVE_CHAIN_RESPONSE
        chain = adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))
        ce = next(c for c in chain if c["security_id"] == 49081)
        assert ce["symbol"] == "NIFTY 28JUL26 23800 CE"

    def test_missing_symbol_in_master_yields_empty_symbol(self):
        # Contract absent from the instrument master -> symbol stays ""
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



class TestOptionChainValidation:
    """Option chain must reject non-optionable instruments with clear error."""

    def test_equity_nse_raises_option_chain_not_supported(self):
        adapter, _client, _ = _adapter()
        with pytest.raises(OptionChainNotSupported, match="TCS"):
            adapter.get_option_chain("TCS", "NSE")

    def test_equity_bse_raises_option_chain_not_supported(self):
        adapter, _client, _ = _adapter()
        with pytest.raises(OptionChainNotSupported, match="RELIANCE"):
            adapter.get_option_chain("RELIANCE", "BSE")

    def test_index_idx_i_succeeds(self):
        adapter, client, _ = _adapter()
        client.post.side_effect = [
            {"data": ["2026-07-28"]},
            LIVE_CHAIN_RESPONSE,
        ]
        chain = adapter.get_option_chain("NIFTY", "NSE")
        assert len(chain) > 0

    def test_fno_nse_fno_succeeds(self):
        client = MagicMock(spec=DhanHttpClient)
        resolver = SymbolResolver()
        resolver.load_from_rows([
            _row(SEM_TRADING_SYMBOL="TCS", SEM_SMST_SECURITY_ID="49081",
                 SEM_SEGMENT="D", SEM_INSTRUMENT_NAME="OPTSTK",
                 SEM_EXPIRY_DATE="2026-07-28", SEM_STRIKE_PRICE=24000.0,
                 SEM_OPTION_TYPE="CE", SM_SYMBOL_NAME="TCS"),
        ])
        adapter = OptionChainAdapter(client, resolver)
        client.post.side_effect = [
            {"data": ["2026-07-28"]},
            LIVE_CHAIN_RESPONSE,
        ]
        chain = adapter.get_option_chain("TCS", "NSE")
        assert len(chain) > 0

    def test_mcx_commodity_succeeds(self):
        adapter, client, _ = _adapter()
        client.post.side_effect = [
            {"data": ["2026-08-01"]},
            LIVE_CHAIN_RESPONSE,
        ]
        chain = adapter.get_option_chain("GOLD", "MCX")
        assert len(chain) > 0

    def test_commodity_underlying_falls_back_to_futures(self):
        """MCX underlyings like SILVER aren't indexed as direct symbols.

        The fallback logic lives in the resolver
        (``resolve_underlying_for_options``); here we verify the adapter
        delegates and uses the resolver-supplied scrip/segment for the
        /optionchain call.
        """
        adapter, client, _ = _adapter()
        client.post.side_effect = [
            {"data": ["2026-07-30"]},
            LIVE_CHAIN_RESPONSE,
        ]
        chain = adapter.get_option_chain("SILVER", "MCX")
        assert len(chain) > 0
        # expiry list must use the resolver-supplied scrip/segment
        expiry_call = client.post.call_args_list[0]
        assert expiry_call.kwargs["json"] == {
            "UnderlyingScrip": 471725,
            "UnderlyingSeg": "MCX_COMM",
        }

    def test_commodity_underlying_no_futures_reraises(self):
        from scalpr.brokers.dhan.exceptions import InstrumentNotFoundError

        adapter, _client, _ = _adapter()
        with pytest.raises(InstrumentNotFoundError):
            adapter.get_option_chain("GHOST", "MCX")

    def test_error_message_contains_symbol_and_exchange(self):
        adapter, _client, _ = _adapter()
        with pytest.raises(OptionChainNotSupported) as exc_info:
            adapter.get_option_chain("TCS", "NSE")
        assert "TCS" in str(exc_info.value)
        assert "NSE" in str(exc_info.value)


class TestScannerAcceptsAdapterOutput:
    def test_scanner_resolves_by_security_id(self):
        # Live chain rows have security_id but no symbol — scanner must still
        # resolve them via resolver.get_by_security_id
        from scalpr.scanner.options_scanner import OptionsScanner

        adapter, client, _ = _adapter(include_options=True)
        client.post.return_value = LIVE_CHAIN_RESPONSE
        chain = adapter.get_option_chain("NIFTY", "NSE", expiry=date(2026, 7, 28))

        scanner_resolver = SymbolResolver()
        scanner_resolver.load_from_rows([
            _row(SEM_TRADING_SYMBOL="NIFTY 28JUL26 23800 CE", SEM_SMST_SECURITY_ID="49081",
                 SEM_SEGMENT="D", SEM_INSTRUMENT_NAME="OPTIDX",
                 SEM_LOT_UNITS=25,
                 SEM_EXPIRY_DATE="2026-07-28", SEM_STRIKE_PRICE=23800.0,
                 SEM_OPTION_TYPE="CE", SM_SYMBOL_NAME="NIFTY"),
            _row(SEM_TRADING_SYMBOL="NIFTY 28JUL26 23800 PE", SEM_SMST_SECURITY_ID="49082",
                 SEM_SEGMENT="D", SEM_INSTRUMENT_NAME="OPTIDX",
                 SEM_LOT_UNITS=25,
                 SEM_EXPIRY_DATE="2026-07-28", SEM_STRIKE_PRICE=23800.0,
                 SEM_OPTION_TYPE="PE", SM_SYMBOL_NAME="NIFTY"),
        ])
        scanner = OptionsScanner(scanner_resolver, min_oi=1, min_volume=1, max_spread=Decimal("5"))

        picks = scanner.scan(Decimal("23800"), chain)
        assert len(picks) == 2  # CE + PE, both ATM and liquid
        assert {p.security_id for p in picks} == {"49081", "49082"}
