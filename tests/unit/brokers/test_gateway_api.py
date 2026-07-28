"""T-005/B-006: Gateway.instrument() domain-first API tests."""
from unittest.mock import MagicMock
from decimal import Decimal

import pytest

from scalpr.domain.instrument import (
    Exchange,
    Segment,
    SimpleInstrumentId,
    ResolvedInstrument,
)


def _make_resolved(symbol="TCS", exchange=Exchange.NSE, segment=Segment.EQUITY, wire="NSE_EQ"):
    return ResolvedInstrument(
        instrument_id=SimpleInstrumentId(symbol=symbol, exchange=exchange),
        security_id="2885",
        exchange=exchange,
        segment=segment,
        trading_symbol=symbol,
        wire_segment=wire,
        lot_size=1,
        tick_size=Decimal("0.05"),
        freeze_quantity=None,
        expiry=None,
        strike=None,
        option_type=None,
    )


def _gateway_with_mock(resolved=None):
    """Create a Gateway with a mocked underlying broker gateway."""
    from scalpr.brokers.gateway import Gateway

    gw = Gateway.__new__(Gateway)
    gw._registry = MagicMock()
    gw._ws_manager = None
    gw._feed_subscribers = {}
    gw._connected = True

    mock_conn = MagicMock()
    mock_resolver = MagicMock()
    mock_resolver.resolve_full.return_value = resolved or _make_resolved()
    mock_conn.resolver = mock_resolver
    mock_conn.market_data = MagicMock()
    mock_conn.historical = MagicMock()

    # _gateway is the underlying broker gateway (e.g. DhanGateway)
    mock_broker_gw = MagicMock()
    mock_broker_gw.connection = mock_conn
    gw._gateway = mock_broker_gw
    return gw, mock_conn


class TestGatewayInstrumentQualifiedString:
    """gw.instrument('TCS:NSE') — existing qualified string path."""

    def test_resolves_qualified_string(self):
        resolved = _make_resolved()
        gw, conn = _gateway_with_mock(resolved)
        handle = gw.instrument("TCS:NSE")
        assert handle.symbol == "TCS"
        conn.resolver.resolve_full.assert_called_once_with("TCS", "NSE")

    def test_raises_for_non_string_identifier(self):
        gw, _ = _gateway_with_mock()
        with pytest.raises(ValueError, match="identifier must be"):
            gw.instrument(12345)  # type: ignore


class TestGatewayInstrumentSeparateArgs:
    """B-006: gw.instrument('TCS', Exchange.NSE) — separate args."""

    def test_exchange_enum_arg(self):
        resolved = _make_resolved()
        gw, conn = _gateway_with_mock(resolved)
        handle = gw.instrument("TCS", Exchange.NSE)
        assert handle.symbol == "TCS"
        conn.resolver.resolve_full.assert_called_once_with("TCS", "NSE")

    def test_exchange_string_arg(self):
        resolved = _make_resolved()
        gw, conn = _gateway_with_mock(resolved)
        handle = gw.instrument("TCS", "NSE")
        assert handle.symbol == "TCS"
        conn.resolver.resolve_full.assert_called_once_with("TCS", "NSE")

    def test_exchange_mcx_string(self):
        resolved = _make_resolved("CRUDEOIL", Exchange.MCX, Segment.COMMODITY, "MCX_COMM")
        gw, conn = _gateway_with_mock(resolved)
        handle = gw.instrument("CRUDEOIL", "MCX")
        conn.resolver.resolve_full.assert_called_once_with("CRUDEOIL", "MCX")

    def test_exchange_mcx_enum(self):
        resolved = _make_resolved("CRUDEOIL", Exchange.MCX, Segment.COMMODITY, "MCX_COMM")
        gw, conn = _gateway_with_mock(resolved)
        handle = gw.instrument("CRUDEOIL", Exchange.MCX)
        conn.resolver.resolve_full.assert_called_once_with("CRUDEOIL", "MCX")

    def test_default_exchange_is_nse(self):
        """When no exchange given, defaults to NSE."""
        resolved = _make_resolved()
        gw, conn = _gateway_with_mock(resolved)
        handle = gw.instrument("TCS")
        conn.resolver.resolve_full.assert_called_once_with("TCS", "NSE")

    def test_index_with_segment_arg(self):
        resolved = _make_resolved("NIFTY", Exchange.NSE, Segment.INDEX, "IDX_I")
        gw, conn = _gateway_with_mock(resolved)
        handle = gw.instrument("NIFTY", Exchange.NSE, Segment.INDEX)
        conn.resolver.resolve_full.assert_called_once_with("NIFTY", "NSE")


class TestGatewayInstrumentSimpleInstrumentId:
    """gw.instrument(SimpleInstrumentId(...)) — domain object path."""

    def test_simple_instrument_id(self):
        resolved = _make_resolved()
        gw, conn = _gateway_with_mock(resolved)
        sid = SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE)
        handle = gw.instrument(sid)
        conn.resolver.resolve_full.assert_called_once_with("TCS", "NSE")


class TestGatewayInstrumentNotFound:
    """Instrument not found → InstrumentNotFound raised."""

    def test_unknown_symbol_raises(self):
        from scalpr.brokers.errors import InstrumentNotFound
        from scalpr.brokers.dhan.exceptions import InstrumentNotFoundError

        gw, conn = _gateway_with_mock()
        conn.resolver.resolve_full.side_effect = InstrumentNotFoundError("UNKNOWN")
        with pytest.raises(InstrumentNotFound):
            gw.instrument("UNKNOWN:NSE")
