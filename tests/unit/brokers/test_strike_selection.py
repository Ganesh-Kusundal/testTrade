"""Tests for strike_selection() across adapter, handle, and facade."""
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
    """Build a synthetic option chain with strikes 23000..25000 step 100."""
    chain = []
    for strike in range(23000, 25100, 100):
        s = Decimal(str(strike))
        # CE gets cheaper as strike goes up; PE gets more expensive
        ce_ltp = Decimal(str(max(25500 - strike, 0)))
        pe_ltp = Decimal(str(max(strike - 24400, 0)))
        for ot, ltp in (("CE", ce_ltp), ("PE", pe_ltp)):
            chain.append({
                "symbol": f"NIFTY STRIKE {strike} {ot}",
                "security_id": str(strike),
                "strike": s,
                "option_type": ot,
                "bid": ltp,
                "ask": ltp + Decimal("1"),
                "oi": 1000,
                "volume": 500,
                "ltp": ltp,
                "delta": Decimal("0.5"),
                "theta": Decimal("-1.0"),
                "gamma": Decimal("0.01"),
                "vega": Decimal("0.02"),
                "iv": Decimal("15.0"),
            })
    return chain


# ── Adapter tests ─────────────────────────────────────────────────────────


class TestAdapterSelectStrikes:
    def test_atm_returns_nearest_strike(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        adapter = OptionChainAdapter(mock_client, mock_resolver)
        chain = _make_chain()
        adapter.get_option_chain = MagicMock(return_value=chain)

        result = adapter.select_strikes(
            "NIFTY", "NSE", mode="ATM", spot_price=Decimal("24050")
        )
        # ATM = strike closest to 24050 → 24100 (distance 50) vs 24000 (distance 100)
        # Actually 24000 is distance 50, 24100 is distance 50 → tie → min picks first
        assert len(result) == 1
        assert result[0] in (Decimal("24000"), Decimal("24100"))

    def test_itm_returns_strikes_below_atm(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        adapter = OptionChainAdapter(mock_client, mock_resolver)
        chain = _make_chain()
        adapter.get_option_chain = MagicMock(return_value=chain)

        result = adapter.select_strikes(
            "NIFTY", "NSE", mode="ITM", count=3, spot_price=Decimal("24000")
        )
        # ATM = 24000, ITM = strikes below ATM = 23000..23900
        # count=3 → last 3 below ATM
        assert len(result) == 3
        assert all(s < Decimal("24000") for s in result)

    def test_otm_returns_strikes_above_atm(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        adapter = OptionChainAdapter(mock_client, mock_resolver)
        chain = _make_chain()
        adapter.get_option_chain = MagicMock(return_value=chain)

        result = adapter.select_strikes(
            "NIFTY", "NSE", mode="OTM", count=3, spot_price=Decimal("24000")
        )
        assert len(result) == 3
        assert all(s > Decimal("24000") for s in result)

    def test_combined_mode_returns_union(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        adapter = OptionChainAdapter(mock_client, mock_resolver)
        chain = _make_chain()
        adapter.get_option_chain = MagicMock(return_value=chain)

        result = adapter.select_strikes(
            "NIFTY", "NSE", mode="ITM,OTM", count=2, spot_price=Decimal("24000")
        )
        # 2 ITM below + 2 OTM above (no ATM in this mode)
        assert len(result) == 4
        below = [s for s in result if s < Decimal("24000")]
        above = [s for s in result if s > Decimal("24000")]
        assert len(below) == 2
        assert len(above) == 2

    def test_empty_chain_returns_empty(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        adapter = OptionChainAdapter(mock_client, mock_resolver)
        adapter.get_option_chain = MagicMock(return_value=[])

        result = adapter.select_strikes("NIFTY", "NSE")
        assert result == []

    def test_no_spot_approximates_from_chain(self):
        mock_client = MagicMock()
        mock_resolver = MagicMock()
        adapter = OptionChainAdapter(mock_client, mock_resolver)
        chain = _make_chain()
        adapter.get_option_chain = MagicMock(return_value=chain)

        # spot_price=None → approximated via put-call parity
        result = adapter.select_strikes(
            "NIFTY", "NSE", mode="ATM", spot_price=None
        )
        assert len(result) == 1
        # The approximated spot is the strike where |CE LTP - PE LTP| is min
        # From _make_chain: CE LTP = max(25500-strike,0), PE LTP = max(strike-24400,0)
        # |CE-PE| = |25500-strike - (strike-24400)| = |49900 - 2*strike|
        # Minimized at strike ≈ 24950 → 24900 and 25000 tie at distance 100;
        # min() picks the first encountered in sorted order → 24900
        assert result[0] == Decimal("24900")


# ── InstrumentHandle tests ────────────────────────────────────────────────


class TestHandleStrikeSelection:
    def test_delegates_to_adapter(self):
        resolved = _make_resolved()
        mock_oc = MagicMock()
        mock_oc.select_strikes.return_value = [Decimal("24000")]
        mock_oc.get_expiry_dates.return_value = [date(2026, 7, 25)]

        mock_market = MagicMock()
        mock_market.get_ltp_by_id.return_value = Decimal("24050")

        handle = InstrumentHandle(
            resolved=resolved,
            market_data_adapter=mock_market,
            historical_adapter=MagicMock(),
            option_chain_adapter=mock_oc,
        )
        result = handle.strike_selection(mode="ATM", count=5)
        assert result == [Decimal("24000")]
        mock_oc.select_strikes.assert_called_once()

    def test_no_adapter_raises(self):
        resolved = _make_resolved(symbol="TCS", segment=Segment.EQUITY)
        handle = InstrumentHandle(
            resolved=resolved,
            market_data_adapter=MagicMock(),
            historical_adapter=MagicMock(),
            option_chain_adapter=None,
        )
        with pytest.raises(OptionChainNotSupported):
            handle.strike_selection()
