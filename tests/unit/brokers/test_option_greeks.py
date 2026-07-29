"""Tests for option_greeks() across adapter, handle, and facade."""
from datetime import date
from decimal import Decimal
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


def _make_chain():
    """Build a synthetic option chain with a few strikes."""
    chain = []
    for strike in [24000, 24100, 24200]:
        s = Decimal(str(strike))
        for ot in ["CE", "PE"]:
            chain.append({
                "symbol": f"NIFTY {strike} {ot}",
                "security_id": str(strike),
                "strike": s,
                "option_type": ot,
                "bid": Decimal("100"),
                "ask": Decimal("101"),
                "oi": 1000,
                "volume": 500,
                "ltp": Decimal("100.5"),
                "delta": Decimal("0.5"),
                "theta": Decimal("-1.0"),
                "gamma": Decimal("0.01"),
                "vega": Decimal("0.02"),
                "iv": Decimal("15.0"),
            })
    return chain


# ── Adapter tests ─────────────────────────────────────────────────────────


class TestAdapterGetOptionGreeks:
    def test_returns_all_greeks_for_valid_leg(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        adapter = OptionChainAdapter(mock_client, mock_resolver)
        chain = _make_chain()
        adapter.get_option_chain = MagicMock(return_value=chain)

        result = adapter.get_option_greeks(
            "NIFTY", "NSE", Decimal("24100"), date(2026, 7, 25), "CE"
        )
        assert result is not None
        assert result["underlying"] == "NIFTY"
        assert result["strike"] == Decimal("24100")
        assert result["expiry"] == date(2026, 7, 25)
        assert result["option_type"] == "CE"
        assert result["delta"] == Decimal("0.5")
        assert result["theta"] == Decimal("-1.0")
        assert result["gamma"] == Decimal("0.01")
        assert result["vega"] == Decimal("0.02")
        assert result["iv"] == Decimal("15.0")
        assert result["ltp"] == Decimal("100.5")
        assert result["oi"] == 1000
        assert result["volume"] == 500

    def test_returns_none_for_missing_strike(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        adapter = OptionChainAdapter(mock_client, mock_resolver)
        chain = _make_chain()
        adapter.get_option_chain = MagicMock(return_value=chain)

        result = adapter.get_option_greeks(
            "NIFTY", "NSE", Decimal("99999"), date(2026, 7, 25), "CE"
        )
        assert result is None

    def test_returns_none_for_wrong_option_type(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        adapter = OptionChainAdapter(mock_client, mock_resolver)
        chain = _make_chain()
        adapter.get_option_chain = MagicMock(return_value=chain)

        # Strike exists but option_type doesn't match
        result = adapter.get_option_greeks(
            "NIFTY", "NSE", Decimal("24100"), date(2026, 7, 25), "INVALID"
        )
        assert result is None


# ── InstrumentHandle tests ────────────────────────────────────────────────


class TestHandleOptionGreeks:
    def test_delegates_to_adapter(self):
        resolved = _make_resolved()
        mock_oc = MagicMock()
        mock_oc.get_option_greeks.return_value = {"delta": Decimal("0.5")}

        handle = InstrumentHandle(
            resolved=resolved,
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
            option_chain_adapter=mock_oc,
        )
        result = handle.option_greeks(
            Decimal("24100"), "CE", date(2026, 7, 25)
        )
        assert result == {"delta": Decimal("0.5")}
        mock_oc.get_option_greeks.assert_called_once_with(
            "NIFTY", "NSE", Decimal("24100"), date(2026, 7, 25), "CE"
        )

    def test_no_adapter_raises(self):
        resolved = _make_resolved(symbol="TCS", segment=Segment.EQUITY)
        handle = InstrumentHandle(
            resolved=resolved,
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
            option_chain_adapter=None,
        )
        with pytest.raises(OptionChainNotSupported):
            handle.option_greeks(Decimal("24100"), "CE", date(2026, 7, 25))
