"""Tests for InstrumentId value objects."""
from datetime import date
from decimal import Decimal

import pytest

from scalpr.domain.instrument import (
    DerivativeInstrumentId,
    Exchange,
    OptionType,
    Segment,
    SimpleInstrumentId,
)


class TestSimpleInstrumentId:
    """SimpleInstrumentId for equity/index identifiers."""

    def test_parse_valid_nse(self):
        inst = SimpleInstrumentId.parse("TCS:NSE")
        assert inst.symbol == "TCS"
        assert inst.exchange == Exchange.NSE

    def test_parse_valid_bse(self):
        inst = SimpleInstrumentId.parse("RELIANCE:BSE")
        assert inst.symbol == "RELIANCE"
        assert inst.exchange == Exchange.BSE

    def test_parse_valid_mcx(self):
        inst = SimpleInstrumentId.parse("GOLD:MCX")
        assert inst.symbol == "GOLD"
        assert inst.exchange == Exchange.MCX

    def test_parse_uppercases_symbol(self):
        inst = SimpleInstrumentId.parse("tcs:nse")
        assert inst.symbol == "TCS"
        assert inst.exchange == Exchange.NSE

    def test_parse_strips_whitespace(self):
        inst = SimpleInstrumentId.parse("  TCS : NSE  ")
        assert inst.symbol == "TCS"
        assert inst.exchange == Exchange.NSE

    def test_parse_invalid_format_no_colon(self):
        with pytest.raises(ValueError, match="Expected 'SYMBOL:EXCHANGE'"):
            SimpleInstrumentId.parse("TCSNSE")

    def test_parse_invalid_format_too_many_colons(self):
        with pytest.raises(ValueError, match="Expected 'SYMBOL:EXCHANGE'"):
            SimpleInstrumentId.parse("TCS:NSE:EXTRA")

    def test_parse_unknown_exchange(self):
        with pytest.raises(ValueError, match="Unknown exchange"):
            SimpleInstrumentId.parse("TCS:UNKNOWN")

    def test_parse_empty_symbol(self):
        with pytest.raises(ValueError, match="Empty symbol"):
            SimpleInstrumentId.parse(":NSE")

    def test_str_representation(self):
        inst = SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE)
        assert str(inst) == "TCS:NSE"

    def test_frozen(self):
        inst = SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE)
        with pytest.raises(AttributeError):
            inst.symbol = "RELIANCE"

    def test_equality(self):
        inst1 = SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE)
        inst2 = SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE)
        assert inst1 == inst2

    def test_hashable(self):
        inst = SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE)
        assert hash(inst) is not None
        # Can be used as dict key
        d = {inst: "value"}
        assert d[inst] == "value"


class TestDerivativeInstrumentId:
    """DerivativeInstrumentId for structured derivatives."""

    def test_futures_creation(self):
        fut = DerivativeInstrumentId(
            underlying="NIFTY",
            exchange=Exchange.NSE,
            segment=Segment.FUTURES,
            expiry=date(2026, 7, 30),
        )
        assert fut.underlying == "NIFTY"
        assert fut.exchange == Exchange.NSE
        assert fut.segment == Segment.FUTURES
        assert fut.expiry == date(2026, 7, 30)
        assert fut.strike is None
        assert fut.option_type is None

    def test_options_creation(self):
        call = DerivativeInstrumentId(
            underlying="NIFTY",
            exchange=Exchange.NSE,
            segment=Segment.OPTIONS,
            expiry=date(2026, 7, 30),
            strike=Decimal("24200"),
            option_type=OptionType.CE,
        )
        assert call.underlying == "NIFTY"
        assert call.segment == Segment.OPTIONS
        assert call.strike == Decimal("24200")
        assert call.option_type == OptionType.CE

    def test_options_requires_strike(self):
        with pytest.raises(ValueError, match="OPTIONS segment requires strike"):
            DerivativeInstrumentId(
                underlying="NIFTY",
                exchange=Exchange.NSE,
                segment=Segment.OPTIONS,
                expiry=date(2026, 7, 30),
                option_type=OptionType.CE,
            )

    def test_options_requires_option_type(self):
        with pytest.raises(ValueError, match="OPTIONS segment requires option_type"):
            DerivativeInstrumentId(
                underlying="NIFTY",
                exchange=Exchange.NSE,
                segment=Segment.OPTIONS,
                expiry=date(2026, 7, 30),
                strike=Decimal("24200"),
            )

    def test_commodity_creation(self):
        commodity = DerivativeInstrumentId(
            underlying="GOLD",
            exchange=Exchange.MCX,
            segment=Segment.COMMODITY,
            expiry=date(2026, 12, 30),
        )
        assert commodity.underlying == "GOLD"
        assert commodity.exchange == Exchange.MCX
        assert commodity.segment == Segment.COMMODITY

    def test_invalid_segment_raises(self):
        with pytest.raises(ValueError, match="requires FUTURES, OPTIONS, or COMMODITY"):
            DerivativeInstrumentId(
                underlying="NIFTY",
                exchange=Exchange.NSE,
                segment=Segment.EQUITY,
                expiry=date(2026, 7, 30),
            )

    def test_frozen(self):
        fut = DerivativeInstrumentId(
            underlying="NIFTY",
            exchange=Exchange.NSE,
            segment=Segment.FUTURES,
            expiry=date(2026, 7, 30),
        )
        with pytest.raises(AttributeError):
            fut.underlying = "BANKNIFTY"
