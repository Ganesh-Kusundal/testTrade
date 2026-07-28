"""T-005/B-006: Gateway.instrument() domain-first API tests."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from scalpr.domain.instrument import (
    Exchange,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
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
    from scalpr.brokers.registry import BrokerRegistry

    gw = Gateway.__new__(Gateway)
    gw._broker_name = "dhan"
    gw._registry = MagicMock()
    gw._ws_manager = None
    gw._ws_loop = None
    gw._ws_thread = None
    gw._stream_callbacks = []
    gw._ws_lock = __import__("threading").Lock()
    gw._connected = True

    mock_conn = MagicMock()
    mock_resolver = MagicMock()
    mock_resolver.resolve_full.return_value = resolved or _make_resolved()
    mock_conn.resolver = mock_resolver
    mock_conn.market_data = MagicMock()
    mock_conn.historical = MagicMock()
    mock_conn.http_client = MagicMock()

    # Mock OptionChainAdapter for registry lookup
    mock_oc_adapter_cls = MagicMock()
    mock_oc_adapter_cls.return_value = MagicMock()
    BrokerRegistry.register_adapter("dhan", "option_chain", mock_oc_adapter_cls)

    # _gateway is the underlying broker gateway (e.g. DhanGateway)
    mock_broker_gw = MagicMock()
    mock_broker_gw.connection = mock_conn
    # Mock the adapters() method to return the connection and adapters
    mock_broker_gw.adapters.return_value = {
        "connection": mock_conn,
        "resolver": mock_resolver,
        "http_client": mock_conn.http_client,
    }
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
        gw.instrument("CRUDEOIL", "MCX")
        conn.resolver.resolve_full.assert_called_once_with("CRUDEOIL", "MCX")

    def test_exchange_mcx_enum(self):
        resolved = _make_resolved("CRUDEOIL", Exchange.MCX, Segment.COMMODITY, "MCX_COMM")
        gw, conn = _gateway_with_mock(resolved)
        gw.instrument("CRUDEOIL", Exchange.MCX)
        conn.resolver.resolve_full.assert_called_once_with("CRUDEOIL", "MCX")

    def test_default_exchange_is_nse(self):
        """When no exchange given, defaults to NSE."""
        resolved = _make_resolved()
        gw, conn = _gateway_with_mock(resolved)
        gw.instrument("TCS")
        conn.resolver.resolve_full.assert_called_once_with("TCS", "NSE")

    def test_index_with_segment_arg(self):
        resolved = _make_resolved("NIFTY", Exchange.NSE, Segment.INDEX, "IDX_I")
        gw, conn = _gateway_with_mock(resolved)
        gw.instrument("NIFTY", Exchange.NSE, Segment.INDEX)
        conn.resolver.resolve_full.assert_called_once_with("NIFTY", "NSE")


class TestGatewayInstrumentSimpleInstrumentId:
    """gw.instrument(SimpleInstrumentId(...)) — domain object path."""

    def test_simple_instrument_id(self):
        resolved = _make_resolved()
        gw, conn = _gateway_with_mock(resolved)
        sid = SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE)
        gw.instrument(sid)
        conn.resolver.resolve_full.assert_called_once_with("TCS", "NSE")


class TestGatewayInstrumentNotFound:
    """Instrument not found → InstrumentNotFound raised."""

    def test_unknown_symbol_raises(self):
        from scalpr.brokers.dhan.exceptions import InstrumentNotFoundError
        from scalpr.brokers.errors import InstrumentNotFound

        gw, conn = _gateway_with_mock()
        conn.resolver.resolve_full.side_effect = InstrumentNotFoundError("UNKNOWN")
        with pytest.raises(InstrumentNotFound):
            gw.instrument("UNKNOWN:NSE")


class TestInstrumentHandleOptionChain:
    """InstrumentHandle.option_chain() — rejects non-optionable instruments."""

    def test_equity_option_chain_raises(self):
        """tcs.option_chain() on NSE_EQ must raise OptionChainNotSupported."""
        from scalpr.brokers.errors import OptionChainNotSupported

        resolved = _make_resolved("TCS", Exchange.NSE, Segment.EQUITY, "NSE_EQ")
        gw, _ = _gateway_with_mock(resolved)
        handle = gw.instrument("TCS:NSE")
        with pytest.raises(OptionChainNotSupported, match="TCS"):
            handle.option_chain()

    def test_index_option_chain_succeeds(self):
        """nifty.option_chain() on IDX_I should delegate to adapter."""
        resolved = _make_resolved("NIFTY", Exchange.NSE, Segment.INDEX, "IDX_I")
        gw, _conn = _gateway_with_mock(resolved)
        handle = gw.instrument("NIFTY:NSE")
        # The adapter is created inside instrument(), mock its get_option_chain
        handle._option_chain = MagicMock()
        handle._option_chain.get_option_chain.return_value = [{"strike": 24000}]
        result = handle.option_chain()
        assert len(result) == 1
        handle._option_chain.get_option_chain.assert_called_once()

    def test_fno_option_chain_succeeds(self):
        """F&O instrument option_chain() should work."""
        resolved = _make_resolved("NIFTY", Exchange.NSE, Segment.FUTURES, "NSE_FNO")
        gw, _ = _gateway_with_mock(resolved)
        handle = gw.instrument("NIFTY:NSE")
        handle._option_chain = MagicMock()
        handle._option_chain.get_option_chain.return_value = []
        result = handle.option_chain(expiry=date(2026, 7, 30))
        assert result == []


class TestInstrumentHandleIdProperty:
    """InstrumentHandle.id — returns the instrument_id."""

    def test_id_returns_instrument_id(self):
        resolved = _make_resolved()
        gw, _ = _gateway_with_mock(resolved)
        handle = gw.instrument("TCS:NSE")
        assert handle.id == resolved.instrument_id
        assert handle.id.symbol == "TCS"
        assert handle.id.exchange == Exchange.NSE


class TestInstrumentHandleSubscribe:
    """InstrumentHandle.subscribe() — WS not available raises RuntimeError."""

    def test_subscribe_without_ws_raiseses_runtime_error(self):
        resolved = _make_resolved()
        gw, _ = _gateway_with_mock(resolved)
        handle = gw.instrument("TCS:NSE")
        with pytest.raises(RuntimeError, match="WebSocket manager not available"):
            handle.subscribe("full", lambda e: None)
