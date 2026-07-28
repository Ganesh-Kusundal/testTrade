"""Tests for future_script() across resolver, adapter, handle, and facade."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from scalpr.brokers.dhan.option_chain import OptionChainAdapter
from scalpr.brokers.dhan.resolver import SymbolResolver
from scalpr.brokers.errors import OptionChainNotSupported
from scalpr.brokers.instrument_handle import InstrumentHandle
from scalpr.domain.instrument import (
    Exchange,
    Instrument,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)


def _make_future(symbol, expiry):
    return Instrument(
        symbol=symbol,
        exchange=Exchange.NSE,
        segment=Segment.FUTURES,
        security_id="99999",
        lot_size=25,
        tick_size=Decimal("0.05"),
        expiry=expiry,
    )


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


# ── Resolver tests ────────────────────────────────────────────────────────


class TestResolverGetFuturesForUnderlying:
    def test_returns_sorted_futures(self):
        resolver = SymbolResolver()
        f1 = _make_future("NIFTY 25 JUL 26 FUT", date(2026, 7, 25))
        f2 = _make_future("NIFTY 28 AUG 26 FUT", date(2026, 8, 28))
        resolver._by_underlying[("NIFTY", Exchange.NSE)] = [f2, f1]
        result = resolver.get_futures_for_underlying("NIFTY", "NSE")
        assert len(result) == 2
        assert result[0].expiry < result[1].expiry

    def test_empty_for_unknown_underlying(self):
        resolver = SymbolResolver()
        result = resolver.get_futures_for_underlying("ZZZ", "NSE")
        assert result == []

    def test_excludes_options(self):
        resolver = SymbolResolver()
        fut = _make_future("NIFTY 25 JUL 26 FUT", date(2026, 7, 25))
        opt = Instrument(
            symbol="NIFTY 25 JUL 26 24000 CE",
            exchange=Exchange.NSE,
            segment=Segment.OPTIONS,
            security_id="88888",
            lot_size=25,
            tick_size=Decimal("0.05"),
            expiry=date(2026, 7, 25),
            strike=Decimal("24000"),
            option_type=__import__("scalpr.domain.instrument", fromlist=["OptionType"]).OptionType.CE,
        )
        resolver._by_underlying[("NIFTY", Exchange.NSE)] = [fut, opt]
        result = resolver.get_futures_for_underlying("NIFTY", "NSE")
        assert len(result) == 1
        assert result[0].segment == Segment.FUTURES


# ── Adapter tests ─────────────────────────────────────────────────────────


class TestAdapterGetFutureSymbol:
    def test_returns_nearest_future(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        future_inst = _make_future("NIFTY 25 JUL 26 FUT", date(2026, 7, 25))
        mock_resolver.get_futures_for_underlying.return_value = [future_inst]

        adapter = OptionChainAdapter(mock_client, mock_resolver)
        result = adapter.get_future_symbol("NIFTY", "NSE", expiry_idx=0)
        assert result == "NIFTY 25 JUL 26 FUT"

    def test_returns_next_future(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        f1 = _make_future("NIFTY 25 JUL 26 FUT", date(2026, 7, 25))
        f2 = _make_future("NIFTY 28 AUG 26 FUT", date(2026, 8, 28))
        mock_resolver.get_futures_for_underlying.return_value = [f1, f2]

        adapter = OptionChainAdapter(mock_client, mock_resolver)
        result = adapter.get_future_symbol("NIFTY", "NSE", expiry_idx=1)
        assert result == "NIFTY 28 AUG 26 FUT"

    def test_no_futures_raises(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        mock_resolver.get_futures_for_underlying.return_value = []

        adapter = OptionChainAdapter(mock_client, mock_resolver)
        with pytest.raises(ValueError, match="No futures found"):
            adapter.get_future_symbol("ZZZ", "NSE")

    def test_expiry_idx_out_of_range_raises(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        f1 = _make_future("NIFTY 25 JUL 26 FUT", date(2026, 7, 25))
        mock_resolver.get_futures_for_underlying.return_value = [f1]

        adapter = OptionChainAdapter(mock_client, mock_resolver)
        with pytest.raises(ValueError, match="out of range"):
            adapter.get_future_symbol("NIFTY", "NSE", expiry_idx=5)


# ── InstrumentHandle tests ────────────────────────────────────────────────


class TestHandleFutureScript:
    def test_delegates_to_adapter(self):
        resolved = _make_resolved()
        mock_oc = MagicMock()
        mock_oc.get_future_symbol.return_value = "NIFTY 25 JUL 26 FUT"
        handle = InstrumentHandle(
            resolved=resolved,
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
            option_chain_adapter=mock_oc,
        )
        result = handle.future_script(expiry_idx=1)
        assert result == "NIFTY 25 JUL 26 FUT"
        mock_oc.get_future_symbol.assert_called_once_with("NIFTY", "NSE", 1)

    def test_no_adapter_raises(self):
        resolved = _make_resolved(symbol="TCS", segment=Segment.EQUITY)
        handle = InstrumentHandle(
            resolved=resolved,
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
            option_chain_adapter=None,
        )
        with pytest.raises(OptionChainNotSupported):
            handle.future_script()
