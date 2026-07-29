"""Tests for the Dhan instrument mapper and exchange-correct resolution.

Fixture rows mirror real shapes from the cached instrument master CSV
(loader contract: raw SEM_EXM_EXCH_ID/SEM_SEGMENT + explicit WIRE_SEGMENT).
"""

from decimal import Decimal

from scalpr.brokers.dhan.resolution import SymbolResolver, map_row, wire_segment_for
from scalpr.domain.instrument import Exchange, OptionType, Segment


def _row(**overrides) -> dict:
    base = {
        "SEM_EXM_EXCH_ID": "NSE",
        "SEM_SEGMENT": "E",
        "SEM_SMST_SECURITY_ID": "2885",
        "SEM_INSTRUMENT_NAME": "EQUITY",
        "SEM_TRADING_SYMBOL": "RELIANCE",
        "SEM_LOT_UNITS": 1.0,
        "SEM_TICK_SIZE": 0.05,
        "SEM_EXPIRY_DATE": None,
        "SEM_STRIKE_PRICE": None,
        "SEM_OPTION_TYPE": None,
        "SEM_CUSTOM_SYMBOL": None,
        "SM_SYMBOL_NAME": None,
    }
    base.update(overrides)
    return base


# ── map_row: exchange / wire segment ────────────────────────────────────

class TestExchangeMapping:
    def test_nse_equity(self):
        m = map_row(_row())
        assert m.instrument.exchange is Exchange.NSE
        assert m.wire_segment == "NSE_EQ"
        assert m.instrument.security_id == "2885"

    def test_bse_equity_maps_to_bse_not_nse(self):
        """The live bug: BSE_EQ rows were defaulting to NSE."""
        m = map_row(_row(SEM_EXM_EXCH_ID="BSE", SEM_SMST_SECURITY_ID="500325"))
        assert m.instrument.exchange is Exchange.BSE
        assert m.wire_segment == "BSE_EQ"

    def test_explicit_wire_segment_key_wins(self):
        m = map_row(_row(WIRE_SEGMENT="NSE_EQ"))
        assert m.wire_segment == "NSE_EQ"

    def test_nse_index_keeps_raw_exchange(self):
        m = map_row(_row(
            SEM_SEGMENT="I", SEM_SMST_SECURITY_ID="13",
            SEM_INSTRUMENT_NAME="INDEX", SEM_TRADING_SYMBOL="NIFTY",
        ))
        assert m.wire_segment == "IDX_I"
        assert m.instrument.exchange is Exchange.NSE
        assert m.instrument.segment is Segment.EQUITY

    def test_mcx_futcom(self):
        m = map_row(_row(
            SEM_EXM_EXCH_ID="MCX", SEM_SEGMENT="M",
            SEM_INSTRUMENT_NAME="FUTCOM", SEM_TRADING_SYMBOL="GOLD-05Aug2024-FUT",
            SEM_EXPIRY_DATE="2024-08-05 23:30:00", SM_SYMBOL_NAME="GOLD",
        ))
        assert m.wire_segment == "MCX_COMM"
        assert m.instrument.exchange is Exchange.MCX
        assert m.instrument.segment is Segment.FUTURES

    def test_unknown_segment_pair_skipped(self):
        assert map_row(_row(SEM_SEGMENT="Z")) is None


# ── map_row: instrument vocabulary ──────────────────────────────────────

class TestVocabulary:
    def test_be_and_bond_are_equity(self):
        assert map_row(_row(SEM_INSTRUMENT_NAME="BE")).instrument.segment is Segment.EQUITY
        assert map_row(_row(SEM_INSTRUMENT_NAME="BOND")).instrument.segment is Segment.EQUITY

    def test_unknown_instrument_name_skipped_not_mismapped(self):
        assert map_row(_row(SEM_INSTRUMENT_NAME="WARRANT")) is None

    def test_eq_suffix_stripped_for_equity(self):
        m = map_row(_row(SEM_TRADING_SYMBOL="RELIANCE-EQ"))
        assert m.instrument.symbol == "RELIANCE"

    def test_missing_symbol_or_sid_skipped(self):
        assert map_row(_row(SEM_TRADING_SYMBOL="")) is None
        assert map_row(_row(SEM_SMST_SECURITY_ID="")) is None


# ── map_row: options ────────────────────────────────────────────────────

def _opt_row(**overrides) -> dict:
    base = _row(
        SEM_SEGMENT="D", SEM_INSTRUMENT_NAME="OPTIDX",
        SEM_TRADING_SYMBOL="NIFTY-Aug2024-24000-CE", SEM_SMST_SECURITY_ID="49081",
        SEM_EXPIRY_DATE="2024-08-29 14:30:00", SEM_STRIKE_PRICE=24000.0,
        SEM_OPTION_TYPE="CE", SEM_LOT_UNITS=25.0, SM_SYMBOL_NAME="NIFTY",
    )
    base.update(overrides)
    return base


class TestOptions:
    def test_optidx_row(self):
        m = map_row(_opt_row())
        inst = m.instrument
        assert inst.segment is Segment.OPTIONS
        assert m.wire_segment == "NSE_FNO"
        assert inst.option_type is OptionType.CE
        assert inst.strike == Decimal("24000")
        assert inst.expiry.isoformat() == "2024-08-29"
        assert inst.lot_size == 25

    def test_bse_ca_pa_option_codes(self):
        assert map_row(_opt_row(SEM_OPTION_TYPE="CA")).instrument.option_type is OptionType.CE
        assert map_row(_opt_row(SEM_OPTION_TYPE="PA")).instrument.option_type is OptionType.PE
        assert map_row(_opt_row(SEM_OPTION_TYPE="PE")).instrument.option_type is OptionType.PE

    def test_xx_option_code_is_none(self):
        assert map_row(_opt_row(SEM_OPTION_TYPE="XX")).instrument.option_type is None

    def test_negative_strike_sentinel_is_none(self):
        """Dhan uses -0.01 for 'no strike' (seen on currency rows in the CSV)."""
        m = map_row(_opt_row(
            SEM_INSTRUMENT_NAME="OPTCUR", SEM_STRIKE_PRICE=-0.01, SEM_OPTION_TYPE="XX",
        ))
        assert m.instrument.strike is None

    def test_futcur_row_has_no_strike(self):
        """Real BSE C FUTCUR shape from the cached CSV."""
        m = map_row(_row(
            SEM_EXM_EXCH_ID="BSE", SEM_SEGMENT="C", SEM_SMST_SECURITY_ID="1026077",
            SEM_INSTRUMENT_NAME="FUTCUR", SEM_TRADING_SYMBOL="USDINR-28Aug2024-FUT",
            SEM_EXPIRY_DATE="2024-08-28 14:30:00", SEM_STRIKE_PRICE=-0.01,
            SEM_OPTION_TYPE="XX", SM_SYMBOL_NAME="USDINR",
        ))
        assert m.instrument.segment is Segment.FUTURES
        assert m.instrument.strike is None
        assert m.wire_segment == "BSE_CURRENCY"


# ── map_row: underlying derivation chain ────────────────────────────────

class TestUnderlying:
    def test_from_sm_symbol_name(self):
        m = map_row(_opt_row(SM_SYMBOL_NAME="NIFTY"))
        assert m.underlying == "NIFTY"

    def test_from_custom_symbol_first_word(self):
        m = map_row(_opt_row(SM_SYMBOL_NAME=None, SEM_CUSTOM_SYMBOL="NIFTY AUG 24000 CALL"))
        assert m.underlying == "NIFTY"

    def test_from_hyphen_split(self):
        m = map_row(_opt_row(SM_SYMBOL_NAME=None, SEM_CUSTOM_SYMBOL=None))
        assert m.underlying == "NIFTY"

    def test_from_trailing_fut_regex(self):
        m = map_row(_row(
            SEM_SEGMENT="D", SEM_INSTRUMENT_NAME="FUTSTK",
            SEM_TRADING_SYMBOL="RELIANCE24AUGFUT",
            SEM_EXPIRY_DATE="2024-08-29 14:30:00",
        ))
        assert m.underlying == "RELIANCE"

    def test_equity_has_no_underlying(self):
        assert map_row(_row()).underlying is None


# ── wire_segment_for fallback ───────────────────────────────────────────

class TestWireSegmentFor:
    def test_fallbacks(self):
        assert wire_segment_for(Exchange.NSE, Segment.EQUITY) == "NSE_EQ"
        assert wire_segment_for(Exchange.BSE, Segment.EQUITY) == "BSE_EQ"
        assert wire_segment_for(Exchange.MCX, Segment.FUTURES) == "MCX_COMM"
        assert wire_segment_for(Exchange.NSE, Segment.OPTIONS) == "NSE_FNO"
        assert wire_segment_for(Exchange.BSE, Segment.FUTURES) == "BSE_FNO"


# ── resolver integration: the live regression ───────────────────────────

class TestResolverRegression:
    def _loaded_resolver(self) -> SymbolResolver:
        resolver = SymbolResolver()
        # BSE row FIRST — the order that triggered the live bug (first-write-wins)
        resolver.load_from_rows([
            _row(SEM_EXM_EXCH_ID="BSE", SEM_SMST_SECURITY_ID="500325"),
            _row(SEM_EXM_EXCH_ID="NSE", SEM_SMST_SECURITY_ID="2885"),
            _row(SEM_SEGMENT="I", SEM_SMST_SECURITY_ID="13",
                 SEM_INSTRUMENT_NAME="INDEX", SEM_TRADING_SYMBOL="NIFTY"),
        ])
        return resolver

    def test_nse_and_bse_reliance_resolve_independently(self):
        resolver = self._loaded_resolver()
        assert resolver.resolve("RELIANCE", "NSE").security_id == "2885"
        assert resolver.resolve("RELIANCE", "BSE").security_id == "500325"

    def test_wire_segment_of(self):
        resolver = self._loaded_resolver()
        assert resolver.wire_segment_of("RELIANCE", "NSE") == "NSE_EQ"
        assert resolver.wire_segment_of("RELIANCE", "BSE") == "BSE_EQ"
        assert resolver.wire_segment_of("NIFTY", "NSE") == "IDX_I"

    def test_unknown_rows_counted_as_skipped(self):
        resolver = SymbolResolver()
        stats = resolver.load_from_rows([
            _row(),
            _row(SEM_INSTRUMENT_NAME="WARRANT", SEM_SMST_SECURITY_ID="999"),
        ])
        assert stats["total"] == 1
        assert stats["skipped"] == 1
