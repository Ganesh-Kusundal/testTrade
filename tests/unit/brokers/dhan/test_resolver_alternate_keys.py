"""Regression tests for flexible option symbol resolution.

Covers B-019: instrument() must accept user-friendly option symbols that
omit the year (e.g. "SILVER 28 JUL 217000 CALL") and use CALL/PUT wording,
resolving to the dash-form master symbol ("SILVER-28Jul2026-217000-CE").
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from scalpr.brokers.dhan.resolution import SymbolResolver, _generate_alternate_keys
from scalpr.domain.instrument import Exchange, Instrument, OptionType, Segment


def _build_resolver() -> SymbolResolver:
    """Populate a resolver with one dash-form MCX option contract."""
    r = SymbolResolver()
    inst = Instrument(
        symbol="SILVER-28Jul2026-217000-CE",
        exchange=Exchange.MCX,
        segment=Segment.OPTIONS,
        security_id="560713",
        lot_size=1,
        tick_size=Decimal("1"),
        option_type=OptionType.CE,
        strike=Decimal("217000"),
        expiry=date(2026, 7, 28),
    )
    # Emulate load_from_rows alternate-key generation for this instrument.
    for key in _generate_alternate_keys(
        inst.symbol, inst.segment, inst.expiry, inst.strike, inst.option_type
    ):
        r._by_symbol[(key, Exchange.MCX)] = inst
    r._by_security_id[inst.security_id] = inst
    r._loaded = True
    return r


class TestOptionSymbolFlexibility:
    def test_yearless_call_resolves(self):
        r = _build_resolver()
        inst = r.resolve_full("SILVER 28 JUL 217000 CALL", "MCX")
        assert inst.security_id == "560713"
        assert inst.trading_symbol == "SILVER-28Jul2026-217000-CE"

    def test_yearless_ce_resolves(self):
        r = _build_resolver()
        inst = r.resolve_full("SILVER 28 JUL 217000 CE", "MCX")
        assert inst.security_id == "560713"

    def test_full_year_resolves(self):
        r = _build_resolver()
        inst = r.resolve_full("SILVER 28 JUL 2026 217000 CE", "MCX")
        assert inst.security_id == "560713"

    def test_stripped_call_resolves(self):
        r = _build_resolver()
        inst = r.resolve_full("SILVER28JUL217000CALL", "MCX")
        assert inst.security_id == "560713"

    def test_generate_alternate_keys_yields_friendly_forms(self):
        keys = _generate_alternate_keys(
            "SILVER-28Jul2026-217000-CE",
            Segment.OPTIONS,
            date(2026, 7, 28),
            Decimal("217000"),
            OptionType.CE,
        )
        assert "SILVER 28 JUL 217000 CE" in keys
        assert "SILVER 28 JUL 2026 217000 CE" in keys
        assert "SILVER28JUL217000CE" in keys


class TestResolveUnderlyingForOptions:
    """Covers D-029: underlying-resolution fallback lives in the resolver."""

    def _resolver_with_future(self) -> tuple[SymbolResolver, str]:
        r = SymbolResolver()
        fut = Instrument(
            symbol="SILVER 30 JUL 2026 FUT",
            exchange=Exchange.MCX,
            segment=Segment.FUTURES,
            security_id="471725",
            lot_size=1,
            tick_size=Decimal("1"),
            expiry=date(2026, 7, 30),
        )
        for key in _generate_alternate_keys(
            fut.symbol, fut.segment, fut.expiry, fut.strike, fut.option_type
        ):
            r._by_symbol[(key, Exchange.MCX)] = fut
        r._by_security_id[fut.security_id] = fut
        r._by_underlying[("SILVER", Exchange.MCX)] = [fut]
        r._wire_by_sid[fut.security_id] = "MCX_COMM"
        # A directly-indexed underlying (e.g. an index) for the direct path.
        nifty = Instrument(
            symbol="NIFTY",
            exchange=Exchange.NSE,
            segment=Segment.INDEX,
            security_id="13",
            lot_size=1,
            tick_size=Decimal("1"),
        )
        r._by_symbol[("NIFTY", Exchange.NSE)] = nifty
        r._by_security_id["13"] = nifty
        r._wire_by_sid["13"] = "IDX_I"
        r._loaded = True
        return r, fut.security_id

    def test_direct_symbol_resolves(self):
        r, _ = self._resolver_with_future()
        sid, seg = r.resolve_underlying_for_options("NIFTY", "NSE")
        assert (sid, seg) == (13, "IDX_I")  # existing NIFTY direct key

    def test_commodity_underlying_falls_back_to_futures(self):

        r, fut_sid = self._resolver_with_future()
        sid, seg = r.resolve_underlying_for_options("SILVER", "MCX")
        assert sid == int(fut_sid)
        assert seg == "MCX_COMM"

    def test_no_futures_reraises(self):
        from scalpr.brokers.dhan.exceptions import InstrumentNotFoundError

        r, _ = self._resolver_with_future()
        with pytest.raises(InstrumentNotFoundError):
            r.resolve_underlying_for_options("GHOST", "MCX")
