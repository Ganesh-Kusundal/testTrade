"""T-005/B-006: Gateway.instrument() domain-first API tests."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from scalpr.domain.instrument import (
    Exchange,
    ResolvedInstrument,
    Segment,
    SimpleInstrumentId,
)
from scalpr.simulation.simulated_gateway import SimulatedGateway


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


# ── Real test doubles (zero MagicMock) ────────────────────────────────────


class _FakeResolver:
    def __init__(self, return_value=None):
        self.calls: list[tuple[str, str]] = []
        self._return_value = return_value
        self._side_effect: BaseException | None = None

    def resolve_full(self, symbol, exchange):
        self.calls.append((symbol, exchange))
        if self._side_effect:
            raise self._side_effect
        return self._return_value if self._return_value is not None else _make_resolved()

    def assert_called_once_with(self, symbol, exchange):
        assert len(self.calls) == 1, f"Expected 1 resolve_full call, got {len(self.calls)}"
        assert self.calls[0] == (symbol, exchange), \
            f"Expected ({symbol!r}, {exchange!r}), got ({self.calls[0][0]!r}, {self.calls[0][1]!r})"


class _FakeMarketData:
    def get_ltp_by_id(self, security_id, wire_segment, symbol=None):
        return "2500.00"

    def get_quote_by_id(self, security_id, wire_segment, symbol=None):
        return {
            "ltp": "2500.00", "open": "2500.00", "high": "2500.00",
            "low": "2500.00", "close": "2500.00", "volume": 0,
        }

    def get_depth_by_id(self, security_id, wire_segment, symbol=None):
        return {"bids": [], "asks": []}


class _FakeHistorical:
    def get_ohlcv(self, symbol, exchange, interval, start, end):
        return []


class _FakeHttpClient:
    def post(self, endpoint, json=None):
        return {}

    def get(self, endpoint):
        return {}

    def put(self, endpoint, json=None):
        return {}

    def delete(self, endpoint):
        return {}

    def update_token(self, access_token):
        pass

    def close(self):
        pass


class _FakeConnection:
    def __init__(self, resolver):
        self.resolver = resolver
        self.market_data = _FakeMarketData()
        self.historical = _FakeHistorical()
        self.http_client = _FakeHttpClient()


class _FakeSimulatedGateway(SimulatedGateway):
    def __init__(self, connection, starting_capital=Decimal("1000000")):
        super().__init__(starting_capital=starting_capital)
        self._fake_connection = connection
        self._connected = True

    @property
    def connection(self):
        return self._fake_connection


class _FakeOptionChainAdapter:
    def __init__(self, http_client=None, resolver=None):
        self.calls: list[tuple] = []
        self._return_value = []

    def get_option_chain(self, underlying, exchange, expiry=None):
        self.calls.append((underlying, exchange, expiry))
        return self._return_value

    def assert_called_once(self):
        assert len(self.calls) == 1, f"Expected 1 get_option_chain call, got {len(self.calls)}"


# ── Gateway factory ──────────────────────────────────────────────────────


def _gateway_with_real_doubles(resolved=None):
    from scalpr.brokers.gateway import Gateway
    from scalpr.brokers.registry import BrokerRegistry

    gw = Gateway.__new__(Gateway)
    gw._broker_name = "dhan"
    gw._registry = None
    gw._ws_manager = None
    gw._ws_loop = None
    gw._ws_thread = None
    gw._stream_callbacks = []
    gw._ws_lock = __import__("threading").Lock()
    gw._connected = True

    resolver = _FakeResolver(return_value=resolved)
    conn = _FakeConnection(resolver=resolver)

    BrokerRegistry.register_adapter("dhan", "option_chain", _FakeOptionChainAdapter)

    gw._gateway = _FakeSimulatedGateway(connection=conn)
    return gw, conn


class TestGatewayInstrumentQualifiedString:
    """gw.instrument('TCS:NSE') — existing qualified string path."""

    def test_resolves_qualified_string(self):
        resolved = _make_resolved()
        gw, conn = _gateway_with_real_doubles(resolved)
        handle = gw.instrument("TCS:NSE")
        assert handle.symbol == "TCS"
        conn.resolver.assert_called_once_with("TCS", "NSE")

    def test_raises_for_non_string_identifier(self):
        gw, _ = _gateway_with_real_doubles()
        with pytest.raises(ValueError, match="identifier must be"):
            gw.instrument(12345)


class TestGatewayInstrumentSeparateArgs:
    """B-006: gw.instrument('TCS', Exchange.NSE) — separate args."""

    def test_exchange_enum_arg(self):
        resolved = _make_resolved()
        gw, conn = _gateway_with_real_doubles(resolved)
        handle = gw.instrument("TCS", Exchange.NSE)
        assert handle.symbol == "TCS"
        conn.resolver.assert_called_once_with("TCS", "NSE")

    def test_exchange_string_arg(self):
        resolved = _make_resolved()
        gw, conn = _gateway_with_real_doubles(resolved)
        handle = gw.instrument("TCS", "NSE")
        assert handle.symbol == "TCS"
        conn.resolver.assert_called_once_with("TCS", "NSE")

    def test_exchange_mcx_string(self):
        resolved = _make_resolved("CRUDEOIL", Exchange.MCX, Segment.COMMODITY, "MCX_COMM")
        gw, conn = _gateway_with_real_doubles(resolved)
        gw.instrument("CRUDEOIL", "MCX")
        conn.resolver.assert_called_once_with("CRUDEOIL", "MCX")

    def test_exchange_mcx_enum(self):
        resolved = _make_resolved("CRUDEOIL", Exchange.MCX, Segment.COMMODITY, "MCX_COMM")
        gw, conn = _gateway_with_real_doubles(resolved)
        gw.instrument("CRUDEOIL", Exchange.MCX)
        conn.resolver.assert_called_once_with("CRUDEOIL", "MCX")

    def test_default_exchange_is_nse(self):
        """When no exchange given, defaults to NSE."""
        resolved = _make_resolved()
        gw, conn = _gateway_with_real_doubles(resolved)
        gw.instrument("TCS")
        conn.resolver.assert_called_once_with("TCS", "NSE")

    def test_index_with_segment_arg(self):
        resolved = _make_resolved("NIFTY", Exchange.NSE, Segment.INDEX, "IDX_I")
        gw, conn = _gateway_with_real_doubles(resolved)
        gw.instrument("NIFTY", Exchange.NSE, Segment.INDEX)
        conn.resolver.assert_called_once_with("NIFTY", "NSE")


class TestGatewayInstrumentSimpleInstrumentId:
    """gw.instrument(SimpleInstrumentId(...)) — domain object path."""

    def test_simple_instrument_id(self):
        resolved = _make_resolved()
        gw, conn = _gateway_with_real_doubles(resolved)
        sid = SimpleInstrumentId(symbol="TCS", exchange=Exchange.NSE)
        gw.instrument(sid)
        conn.resolver.assert_called_once_with("TCS", "NSE")


class TestGatewayInstrumentNotFound:
    """Instrument not found -> InstrumentNotFound raised."""

    def test_unknown_symbol_raises(self):
        from scalpr.brokers.dhan.exceptions import InstrumentNotFoundError
        from scalpr.brokers.errors import InstrumentNotFound

        gw, conn = _gateway_with_real_doubles()
        conn.resolver._side_effect = InstrumentNotFoundError("UNKNOWN")
        with pytest.raises(InstrumentNotFound):
            gw.instrument("UNKNOWN:NSE")


class TestInstrumentHandleOptionChain:
    """InstrumentHandle.option_chain() — rejects non-optionable instruments."""

    def test_equity_option_chain_raises(self):
        """tcs.option_chain() on NSE_EQ must raise OptionChainNotSupported."""
        from scalpr.brokers.errors import OptionChainNotSupported

        resolved = _make_resolved("TCS", Exchange.NSE, Segment.EQUITY, "NSE_EQ")
        gw, _ = _gateway_with_real_doubles(resolved)
        handle = gw.instrument("TCS:NSE")
        with pytest.raises(OptionChainNotSupported, match="TCS"):
            handle.option_chain()

    def test_index_option_chain_succeeds(self):
        """nifty.option_chain() on IDX_I should delegate to adapter."""
        resolved = _make_resolved("NIFTY", Exchange.NSE, Segment.INDEX, "IDX_I")
        gw, _conn = _gateway_with_real_doubles(resolved)
        handle = gw.instrument("NIFTY:NSE")
        handle._option_chain._return_value = [{"strike": 24000}]
        result = handle.option_chain(as_df=False)
        assert len(result) == 1
        handle._option_chain.assert_called_once()

    def test_fno_option_chain_succeeds(self):
        """F&O instrument option_chain() should work."""
        resolved = _make_resolved("NIFTY", Exchange.NSE, Segment.FUTURES, "NSE_FNO")
        gw, _ = _gateway_with_real_doubles(resolved)
        handle = gw.instrument("NIFTY:NSE")
        result = handle.option_chain(expiry=date(2026, 7, 30), as_df=False)
        assert result == []


class TestInstrumentHandleIdProperty:
    """InstrumentHandle.id — returns the instrument_id."""

    def test_id_returns_instrument_id(self):
        resolved = _make_resolved()
        gw, _ = _gateway_with_real_doubles(resolved)
        handle = gw.instrument("TCS:NSE")
        assert handle.id == resolved.instrument_id
        assert handle.id.symbol == "TCS"
        assert handle.id.exchange == Exchange.NSE


class TestInstrumentHandleSubscribe:
    """InstrumentHandle.subscribe() — WS not available raises RuntimeError."""

    def test_subscribe_without_ws_raiseses_runtime_error(self):
        resolved = _make_resolved()
        gw, _ = _gateway_with_real_doubles(resolved)
        handle = gw.instrument("TCS:NSE")
        with pytest.raises(RuntimeError, match="WebSocket manager not available"):
            handle.subscribe("full", lambda e: None)
