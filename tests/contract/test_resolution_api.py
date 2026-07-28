"""Contract tests for the instrument resolution API surface.

Verifies that the public API of the resolution subsystem remains stable
and that the three-file structure (segments, mapper, resolver) maintains
clear boundaries.
"""
from __future__ import annotations

from scalpr.brokers.dhan.instrument_mapper import map_row, wire_segment_for
from scalpr.brokers.dhan.resolver import SymbolResolver
from scalpr.brokers.dhan.segments import (
    EXCHANGE_TO_SEGMENT,
    SEGMENT_TO_EXCHANGE,
    normalise_exchange,
    to_dhan_wire,
)
from scalpr.domain.instrument import Exchange, Instrument, Segment


class TestResolutionArchitecture:
    """Verify the three-file resolution architecture is stable."""

    def test_resolver_is_public_api(self):
        """SymbolResolver is the main entry point for resolution."""
        resolver = SymbolResolver()
        assert hasattr(resolver, "resolve")
        assert hasattr(resolver, "resolve_full")
        assert hasattr(resolver, "load_from_rows")

    def test_mapper_is_pure_function(self):
        """instrument_mapper provides pure functions (no state)."""
        # map_row should be callable without any instance
        assert callable(map_row)
        assert callable(wire_segment_for)

    def test_segments_provides_constants(self):
        """segments.py provides wire-format constants."""
        assert isinstance(EXCHANGE_TO_SEGMENT, dict)
        assert isinstance(SEGMENT_TO_EXCHANGE, dict)
        assert callable(normalise_exchange)
        assert callable(to_dhan_wire)

    def test_resolver_uses_mapper_and_segments(self):
        """SymbolResolver internally uses mapper and segments."""
        resolver = SymbolResolver()
        # Load a sample instrument
        rows = [
            {
                "SEM_TRADING_SYMBOL": "RELIANCE-EQ",
                "SEM_SMST_SECURITY_ID": "2885",
                "SEM_EXM_EXCH_ID": "NSE",
                "SEM_SEGMENT": "E",
                "SEM_INSTRUMENT_NAME": "EQUITY",
                "SEM_LOT_UNITS": "1",
                "SEM_TICK_SIZE": "0.05",
            }
        ]
        resolver.load_from_rows(rows)

        # Resolver should successfully resolve the instrument
        inst = resolver.resolve("RELIANCE", "NSE")
        assert inst.symbol == "RELIANCE"
        assert inst.exchange == Exchange.NSE
        assert inst.segment == Segment.EQUITY


class TestResolverPublicAPI:
    """Verify SymbolResolver's public methods work correctly."""

    def test_resolve_returns_instrument(self):
        """resolve() returns an Instrument for valid symbols."""
        resolver = SymbolResolver()
        rows = [
            {
                "SEM_TRADING_SYMBOL": "TCS",
                "SEM_SMST_SECURITY_ID": "1234",
                "SEM_EXM_EXCH_ID": "NSE",
                "SEM_SEGMENT": "E",
                "SEM_INSTRUMENT_NAME": "EQUITY",
                "SEM_LOT_UNITS": "1",
                "SEM_TICK_SIZE": "0.05",
            }
        ]
        resolver.load_from_rows(rows)

        inst = resolver.resolve("TCS", "NSE")
        assert isinstance(inst, Instrument)
        assert inst.symbol == "TCS"

    def test_resolve_full_returns_resolved_instrument(self):
        """resolve_full() returns a ResolvedInstrument with wire segment."""
        resolver = SymbolResolver()
        rows = [
            {
                "SEM_TRADING_SYMBOL": "INFY",
                "SEM_SMST_SECURITY_ID": "5678",
                "SEM_EXM_EXCH_ID": "NSE",
                "SEM_SEGMENT": "E",
                "SEM_INSTRUMENT_NAME": "EQUITY",
                "SEM_LOT_UNITS": "1",
                "SEM_TICK_SIZE": "0.05",
            }
        ]
        resolver.load_from_rows(rows)

        resolved = resolver.resolve_full("INFY", "NSE")
        assert resolved.security_id == "5678"
        assert resolved.wire_segment == "NSE_EQ"
        assert resolved.exchange == Exchange.NSE

    def test_wire_segment_of_returns_wire_format(self):
        """wire_segment_of() returns the Dhan wire segment string."""
        resolver = SymbolResolver()
        rows = [
            {
                "SEM_TRADING_SYMBOL": "NIFTY",
                "SEM_SMST_SECURITY_ID": "9999",
                "SEM_EXM_EXCH_ID": "NSE",
                "SEM_SEGMENT": "I",
                "SEM_INSTRUMENT_NAME": "INDEX",
                "SEM_LOT_UNITS": "1",
                "SEM_TICK_SIZE": "0.05",
            }
        ]
        resolver.load_from_rows(rows)

        wire = resolver.wire_segment_of("NIFTY", "NSE")
        assert wire == "IDX_I"
