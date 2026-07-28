"""Tests for Dhan wire-segment mappings."""
import pytest

from scalpr.brokers.dhan.instrument_mapper import wire_segment_for
from scalpr.brokers.dhan.segments import (
    exchange_to_wire,
    normalise_exchange,
    to_dhan_wire,
)
from scalpr.domain.instrument import Exchange, Segment


class TestToDhanWire:
    """to_dhan_wire(exchange, segment) → wire string."""

    def test_nse_equity(self):
        assert to_dhan_wire(Exchange.NSE, Segment.EQUITY) == "NSE_EQ"

    def test_bse_equity(self):
        assert to_dhan_wire(Exchange.BSE, Segment.EQUITY) == "BSE_EQ"

    def test_nse_futures(self):
        assert to_dhan_wire(Exchange.NSE, Segment.FUTURES) == "NSE_FNO"

    def test_nse_options(self):
        assert to_dhan_wire(Exchange.NSE, Segment.OPTIONS) == "NSE_FNO"

    def test_bse_futures(self):
        assert to_dhan_wire(Exchange.BSE, Segment.FUTURES) == "BSE_FNO"

    def test_mcx_commodity(self):
        assert to_dhan_wire(Exchange.MCX, Segment.COMMODITY) == "MCX_COMM"

    def test_mcx_futures(self):
        assert to_dhan_wire(Exchange.MCX, Segment.FUTURES) == "MCX_COMM"

    def test_nse_index(self):
        assert to_dhan_wire(Exchange.NSE, Segment.INDEX) == "IDX_I"

    def test_nse_currency(self):
        assert to_dhan_wire(Exchange.NSE, Segment.CURRENCY) == "NSE_CURRENCY"

    def test_mcx_options(self):
        assert to_dhan_wire(Exchange.MCX, Segment.OPTIONS) == "MCX_COMM"

    def test_bse_index(self):
        assert to_dhan_wire(Exchange.BSE, Segment.INDEX) == "IDX_I"

    def test_nse_fno_futures(self):
        assert to_dhan_wire(Exchange.NSE_FNO, Segment.FUTURES) == "NSE_FNO"

    def test_nse_fno_options(self):
        assert to_dhan_wire(Exchange.NSE_FNO, Segment.OPTIONS) == "NSE_FNO"

    def test_unsupported_combination_raises(self):
        with pytest.raises(ValueError, match="No Dhan wire mapping"):
            to_dhan_wire(Exchange.MCX, Segment.EQUITY)


class TestExchangeToWire:
    """exchange_to_wire(exchange) → wire string (legacy 1-arg)."""

    def test_nse_exchange(self):
        assert exchange_to_wire(Exchange.NSE) == "NSE_EQ"

    def test_bse_exchange(self):
        assert exchange_to_wire(Exchange.BSE) == "BSE_EQ"

    def test_mcx_exchange(self):
        assert exchange_to_wire(Exchange.MCX) == "MCX_COMM"

    def test_string_nse(self):
        assert exchange_to_wire("NSE") == "NSE_EQ"

    def test_string_mcx(self):
        assert exchange_to_wire("MCX") == "MCX_COMM"

    def test_unknown_exchange_raises(self):
        with pytest.raises(ValueError, match="Unknown exchange"):
            exchange_to_wire("UNKNOWN")


class TestNormaliseExchange:
    """normalise_exchange(wire_string) → Exchange enum."""

    def test_nse(self):
        assert normalise_exchange("NSE") == Exchange.NSE

    def test_bse(self):
        assert normalise_exchange("BSE") == Exchange.BSE

    def test_mcx(self):
        assert normalise_exchange("MCX") == Exchange.MCX

    def test_nse_eq(self):
        assert normalise_exchange("NSE_EQ") == Exchange.NSE

    def test_bse_eq(self):
        assert normalise_exchange("BSE_EQ") == Exchange.BSE

    def test_mcx_comm(self):
        assert normalise_exchange("MCX_COMM") == Exchange.MCX

    def test_nse_fno(self):
        assert normalise_exchange("NSE_FNO") == Exchange.NSE

    def test_idx_i(self):
        assert normalise_exchange("IDX_I") == Exchange.NSE

    def test_nse_currency(self):
        assert normalise_exchange("NSE_CURRENCY") == Exchange.NSE

    def test_case_insensitive(self):
        assert normalise_exchange("nse") == Exchange.NSE

    def test_unknown_defaults_to_nse(self):
        assert normalise_exchange("UNKNOWN") == Exchange.NSE

    def test_index_storage_key_is_nse(self):
        # index rows are stored under their raw exchange (NSE) per instrument_mapper
        assert normalise_exchange("INDEX") == Exchange.NSE

    def test_currency_storage_key_is_nse(self):
        assert normalise_exchange("CURRENCY") == Exchange.NSE

    def test_strict_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown exchange"):
            normalise_exchange("NSSE", strict=True)

    def test_strict_enum_passthrough(self):
        assert normalise_exchange(Exchange.MCX, strict=True) == Exchange.MCX

    def test_strict_known_string_ok(self):
        assert normalise_exchange("NSE_EQ", strict=True) == Exchange.NSE


class TestWireSegmentForConsolidation:
    """wire_segment_for delegates to the canonical to_dhan_wire table (W1)."""

    def test_nse_index_returns_idx_i(self):
        assert wire_segment_for(Exchange.NSE, Segment.INDEX) == "IDX_I"

    def test_equity_unchanged(self):
        assert wire_segment_for(Exchange.NSE, Segment.EQUITY) == "NSE_EQ"
        assert wire_segment_for(Exchange.BSE, Segment.EQUITY) == "BSE_EQ"

    def test_derivatives_unchanged(self):
        assert wire_segment_for(Exchange.NSE, Segment.FUTURES) == "NSE_FNO"
        assert wire_segment_for(Exchange.BSE, Segment.OPTIONS) == "BSE_FNO"
        assert wire_segment_for(Exchange.MCX, Segment.FUTURES) == "MCX_COMM"

    def test_string_path_knows_nse_fno_and_currency(self):
        assert exchange_to_wire("NSE_FNO") == "NSE_FNO"
        assert exchange_to_wire("CURRENCY") == "NSE_CURRENCY"
