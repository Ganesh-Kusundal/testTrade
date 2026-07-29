"""K-041/K-042: public expiry-list API + consistent option_greeks signature.

K-041 — facade.option_greeks used (underlying, strike, expiry, option_type,
exchange=) with mandatory expiry, diverging from every other option method.
Cure: (underlying, strike, option_type, exchange=, expiry=None) with
expiry=None auto-resolving to the next expiry.

K-042 — expiries were only reachable via adapter._resolve_next_expiry /
_expiry_cache (private). Cure: adapter.get_expiry_dates() +
gw.option_expiries(); InstrumentHandle no longer touches adapter privates.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import ClassVar
from unittest.mock import MagicMock

import pytest

from scalpr.brokers.dhan.option_chain import OptionChainAdapter
from scalpr.brokers.errors import OptionChainNotSupported
from scalpr.brokers.instrument_handle import InstrumentHandle
from scalpr.domain.instrument import (
    Exchange,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)

TODAY = date.today()
NEXT_EXPIRY = TODAY + timedelta(days=7)
FAR_EXPIRY = TODAY + timedelta(days=35)


def _make_resolved(symbol="NIFTY", exchange=Exchange.NSE, segment=Segment.INDEX):
    return ResolvedInstrument(
        instrument_id=SimpleInstrumentId(symbol=symbol, exchange=exchange),
        security_id="13",
        exchange=exchange,
        segment=segment,
        trading_symbol=symbol,
        wire_segment="IDX_I",
        lot_size=25,
        tick_size=Decimal("0.05"),
        freeze_quantity=None,
        expiry=None,
        strike=None,
        option_type=None,
    )


def _adapter_with_expiries() -> tuple[OptionChainAdapter, MagicMock]:
    """Adapter whose HTTP client serves a canned expirylist response."""
    mock_client = MagicMock()
    mock_client.post.return_value = {
        "data": [FAR_EXPIRY.isoformat(), NEXT_EXPIRY.isoformat()]
    }
    mock_resolver = MagicMock()
    mock_resolver.resolve_underlying_for_options.return_value = (13, "IDX_I")
    return OptionChainAdapter(mock_client, mock_resolver), mock_client


# ── K-042: adapter.get_expiry_dates ───────────────────────────────────────


class TestAdapterGetExpiryDates:
    def test_returns_sorted_dates(self):
        adapter, _ = _adapter_with_expiries()
        expiries = adapter.get_expiry_dates("NIFTY", "NSE")
        assert expiries == [NEXT_EXPIRY, FAR_EXPIRY]

    def test_second_call_served_from_cache(self):
        adapter, mock_client = _adapter_with_expiries()
        adapter.get_expiry_dates("NIFTY", "NSE")
        adapter.get_expiry_dates("NIFTY", "NSE")
        assert mock_client.post.call_count == 1

    def test_returns_copy_not_cache_reference(self):
        adapter, _ = _adapter_with_expiries()
        first = adapter.get_expiry_dates("NIFTY", "NSE")
        first.clear()
        assert adapter.get_expiry_dates("NIFTY", "NSE") == [NEXT_EXPIRY, FAR_EXPIRY]

    def test_non_optionable_segment_raises(self):
        adapter, _ = _adapter_with_expiries()
        adapter._resolver.resolve_underlying_for_options.return_value = (2885, "NSE_EQ")
        with pytest.raises(OptionChainNotSupported):
            adapter.get_expiry_dates("TCS", "NSE")


# ── K-041: adapter.get_option_greeks expiry auto-resolve ─────────────────


class TestAdapterGreeksExpiryAutoResolve:
    def _chain(self):
        return [{
            "symbol": "NIFTY 24100 CE", "security_id": "1", "strike": Decimal("24100"),
            "option_type": "CE", "bid": Decimal("100"), "ask": Decimal("101"),
            "oi": 1000, "volume": 500, "ltp": Decimal("100.5"),
            "delta": Decimal("0.5"), "theta": Decimal("-1.0"),
            "gamma": Decimal("0.01"), "vega": Decimal("0.02"), "iv": Decimal("15.0"),
        }]

    def test_expiry_none_resolves_next_expiry(self):
        adapter, _ = _adapter_with_expiries()
        adapter.get_option_chain = MagicMock(return_value=self._chain())

        result = adapter.get_option_greeks(
            "NIFTY", "NSE", Decimal("24100"), None, "CE"
        )
        assert result is not None
        assert result["expiry"] == NEXT_EXPIRY

    def test_explicit_expiry_still_honoured(self):
        adapter, mock_client = _adapter_with_expiries()
        adapter.get_option_chain = MagicMock(return_value=self._chain())

        result = adapter.get_option_greeks(
            "NIFTY", "NSE", Decimal("24100"), FAR_EXPIRY, "CE"
        )
        assert result is not None
        assert result["expiry"] == FAR_EXPIRY
        mock_client.post.assert_not_called()  # no expirylist fetch needed


# ── Facade: gw.option_expiries + new option_greeks signature ─────────────


class _FakeOptionChainAdapter:
    """Registry-compatible fake capturing calls to the two new surfaces."""

    expiries: ClassVar[list[date]] = [NEXT_EXPIRY, FAR_EXPIRY]
    greeks_calls: ClassVar[list[tuple]] = []
    expiry_calls: ClassVar[list[tuple]] = []

    def __init__(self, http_client=None, resolver=None):
        pass

    def get_expiry_dates(self, underlying, exchange):
        type(self).expiry_calls.append((underlying, exchange))
        return list(type(self).expiries)

    def get_option_greeks(self, underlying, exchange, strike, expiry, option_type):
        type(self).greeks_calls.append((underlying, exchange, strike, expiry, option_type))
        return {"underlying": underlying, "expiry": expiry, "delta": Decimal("0.5")}


def _facade_gateway():
    import threading

    from scalpr.brokers.gateway import Gateway
    from scalpr.brokers.registry import BrokerRegistry
    from scalpr.simulation.simulated_gateway import SimulatedGateway

    class _Conn:
        http_client = object()
        resolver = object()

    class _FakeSim(SimulatedGateway):
        connection = _Conn()

    gw = Gateway.__new__(Gateway)
    gw._broker_name = "dhan"
    gw._registry = None
    gw._ws_manager = None
    gw._ws_loop = None
    gw._ws_thread = None
    gw._stream_callbacks = []
    gw._ws_lock = threading.Lock()
    gw._connected = True
    gw._gateway = _FakeSim(starting_capital=Decimal("1000000"))

    _FakeOptionChainAdapter.greeks_calls = []
    _FakeOptionChainAdapter.expiry_calls = []
    BrokerRegistry.register_adapter("dhan", "option_chain", _FakeOptionChainAdapter)
    return gw


class TestFacadeOptionExpiries:
    def test_returns_adapter_expiries(self):
        gw = _facade_gateway()
        assert gw.option_expiries("NIFTY") == [NEXT_EXPIRY, FAR_EXPIRY]
        assert _FakeOptionChainAdapter.expiry_calls == [("NIFTY", "NSE")]

    def test_exchange_kwarg(self):
        gw = _facade_gateway()
        gw.option_expiries("CRUDEOIL", exchange="MCX")
        assert _FakeOptionChainAdapter.expiry_calls == [("CRUDEOIL", "MCX")]


class TestFacadeOptionGreeksSignature:
    def test_natural_call_no_expiry(self):
        """THE regression: (underlying, strike, option_type) must not TypeError."""
        gw = _facade_gateway()
        result = gw.option_greeks("NIFTY", Decimal("24100"), "CE")
        assert result is not None
        assert _FakeOptionChainAdapter.greeks_calls == [
            ("NIFTY", "NSE", Decimal("24100"), None, "CE")
        ]

    def test_mcx_call_with_exchange_kwarg(self):
        gw = _facade_gateway()
        gw.option_greeks("CRUDEOIL", Decimal("7950"), "CE", exchange="MCX")
        assert _FakeOptionChainAdapter.greeks_calls == [
            ("CRUDEOIL", "MCX", Decimal("7950"), None, "CE")
        ]

    def test_explicit_expiry_passed_through(self):
        gw = _facade_gateway()
        gw.option_greeks("NIFTY", Decimal("24100"), "CE", expiry=FAR_EXPIRY)
        assert _FakeOptionChainAdapter.greeks_calls[0][3] == FAR_EXPIRY


# ── InstrumentHandle: no private adapter access ───────────────────────────


class TestHandleUsesPublicExpiryApi:
    def _handle(self, mock_oc):
        return InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
            option_chain_adapter=mock_oc,
        )

    def test_expiry_list_delegates_to_public_api(self):
        mock_oc = MagicMock(spec=OptionChainAdapter)
        mock_oc.get_expiry_dates.return_value = [NEXT_EXPIRY, FAR_EXPIRY]
        handle = self._handle(mock_oc)
        assert handle.expiry_list() == [NEXT_EXPIRY, FAR_EXPIRY]
        mock_oc.get_expiry_dates.assert_called_once_with("NIFTY", "NSE")

    def test_strike_selection_uses_public_expiry_api(self):
        mock_oc = MagicMock(spec=OptionChainAdapter)
        mock_oc.get_expiry_dates.return_value = [NEXT_EXPIRY]
        mock_oc.select_strikes.return_value = [Decimal("24000")]
        mock_market = MagicMock()
        mock_market.get_ltp_by_id.return_value = Decimal("24050")

        handle = InstrumentHandle(
            resolved=_make_resolved(),
            market_data_adapter=mock_market,
            historical_adapter=MagicMock(),
            option_chain_adapter=mock_oc,
        )
        assert handle.strike_selection(mode="ATM", count=5) == [Decimal("24000")]
        mock_oc.get_expiry_dates.assert_called_once_with("NIFTY", "NSE")

    def test_option_greeks_expiry_optional(self):
        mock_oc = MagicMock(spec=OptionChainAdapter)
        mock_oc.get_option_greeks.return_value = {"delta": Decimal("0.5")}
        handle = self._handle(mock_oc)
        result = handle.option_greeks(Decimal("24100"), "CE")
        assert result == {"delta": Decimal("0.5")}
        mock_oc.get_option_greeks.assert_called_once_with(
            "NIFTY", "NSE", Decimal("24100"), None, "CE"
        )
