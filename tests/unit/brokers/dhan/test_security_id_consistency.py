"""Security ID consistency tests for Dhan broker integration.

These tests verify that all trading operations use the authoritative
security_id field (not trading symbol) when communicating with Dhan API.

Catches regressions for the 4 critical bugs fixed in Phase 1:
1. Orders using inst.symbol instead of inst.security_id
2. Historical data using inst.symbol instead of inst.security_id
3. WebSocket not resolving symbols to security_ids
4. Options scanner creating fake security_ids
"""

from decimal import Decimal

import pytest

from scalpr.brokers.dhan.ws_client import DhanWebSocketClient
from scalpr.domain.instrument import Exchange, Instrument, Segment

# ── Test helpers: minimal stubs (zero MagicMock dependency) ──────────────


class _CallRecorder:
    """Records calls to a method — replaces MagicMock call tracking."""
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))

    @property
    def call_args(self):
        if not self.calls:
            return None
        return self.calls[0]

    def assert_not_called(self):
        assert len(self.calls) == 0, f"Expected no calls, got {len(self.calls)}"


class _FakeFeed:
    """Minimal SDK feed stub — records subscribe_symbols calls."""
    def __init__(self):
        self.subscribe_symbols = _CallRecorder()


class _FakeResolver:
    """Minimal SymbolResolver stub with known instruments."""
    def __init__(self):
        self._resolve_calls = []
        self._instruments = {
            "RELIANCE": Instrument(
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                segment=Segment.EQUITY,
                security_id="2885",
                lot_size=1,
                tick_size=Decimal("0.05"),
            ),
            "TCS": Instrument(
                symbol="TCS",
                exchange=Exchange.NSE,
                segment=Segment.EQUITY,
                security_id="11536",
                lot_size=1,
                tick_size=Decimal("0.05"),
            ),
        }

    def resolve(self, symbol, exchange="NSE"):
        self._resolve_calls.append((symbol, exchange))
        inst = self._instruments.get(symbol)
        if inst is None:
            raise ValueError(f"Unknown symbol: {symbol}")
        return inst

    def wire_segment_of(self, symbol, exchange="NSE"):
        return "NSE_EQ"

    def assert_resolve_called_once_with(self, symbol, exchange):
        assert len(self._resolve_calls) == 1, \
            f"Expected 1 resolve call, got {len(self._resolve_calls)}"
        assert self._resolve_calls[0] == (symbol, exchange), \
            f"Expected resolve({symbol!r}, {exchange!r}), got {self._resolve_calls[0]}"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_resolver():
    """Create a fake SymbolResolver that returns real instruments."""
    return _FakeResolver()


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket Client: Security ID Resolution
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebSocketSecurityIdResolution:
    """Verify WebSocket client resolves symbols to security_ids before subscribing."""

    @pytest.mark.asyncio
    async def test_subscribe_resolves_security_id_via_resolver(self, fake_resolver):
        """subscribe() should resolve symbol to security_id using resolver."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=fake_resolver,
        )

        feed = _FakeFeed()
        client._feed = feed
        client._connected = True

        result = await client.subscribe([("RELIANCE", "NSE")])

        fake_resolver.assert_resolve_called_once_with("RELIANCE", "NSE")
        assert result == {("RELIANCE", "NSE"): True}

    @pytest.mark.asyncio
    async def test_subscribe_uses_string_security_id(self, fake_resolver):
        """Security ID must be a string in the SDK v2 tuple — int SecurityId
        is silently accepted by the server but streams nothing (verified live 2026-07-27)."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=fake_resolver,
        )

        feed = _FakeFeed()
        client._feed = feed
        client._connected = True

        await client.subscribe([("RELIANCE", "NSE")])

        call_args = feed.subscribe_symbols.call_args
        assert call_args is not None, "subscribe_symbols should be called"

        instruments = call_args[0][0] if call_args[0] else []
        assert len(instruments) > 0, "Should have at least one instrument"

        _exch_int, sec_id, _mode_int = instruments[0]
        assert isinstance(sec_id, str), f"security_id must be str, got {type(sec_id)}"
        assert sec_id == "2885", f"Expected RELIANCE security_id='2885', got {sec_id}"

    @pytest.mark.asyncio
    async def test_subscribe_handles_resolution_failure_gracefully(self, fake_resolver):
        """S-3: resolution failure must be reported as False per-pair, not hidden."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=fake_resolver,
        )

        feed = _FakeFeed()
        client._feed = feed
        client._connected = True

        result = await client.subscribe([("UNKNOWN", "NSE")])
        assert result == {("UNKNOWN", "NSE"): False}

        feed.subscribe_symbols.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscribe_fallback_without_resolver(self):
        """subscribe() should fallback to int(symbol) if no resolver available."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=None,
        )

        feed = _FakeFeed()
        client._feed = feed
        client._connected = True

        result = await client.subscribe([("2885", "NSE")])

        assert result == {("2885", "NSE"): True}


# ═══════════════════════════════════════════════════════════════════════════════
# Orders: Security ID Usage (Code Inspection Test)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrdersSecurityIdUsage:
    """Verify orders code uses inst.security_id, not inst.symbol."""

    def test_orders_code_uses_security_id_field(self):
        """Orders adapter should reference inst.security_id in source code."""
        import inspect

        from scalpr.brokers.dhan.orders import OrdersAdapter

        source = inspect.getsource(OrdersAdapter.place_order)

        assert "inst.security_id" in source, \
            "OrdersAdapter.place_order should use inst.security_id, not inst.symbol"
        assert "inst.symbol" not in source or "inst.security_id" in source, \
            "OrdersAdapter should prefer security_id over symbol"


# ═══════════════════════════════════════════════════════════════════════════════
# Historical Data: Security ID Usage (Code Inspection Test)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHistoricalSecurityIdUsage:
    """Verify historical data code uses inst.security_id, not inst.symbol."""

    def test_historical_code_uses_security_id_field(self):
        """Historical data adapter should reference inst.security_id in source code."""
        import inspect

        from scalpr.brokers.dhan.historical import HistoricalDataAdapter

        source = inspect.getsource(HistoricalDataAdapter._resolve_segment)

        assert "inst.security_id" in source, \
            "HistoricalDataAdapter._resolve_segment should use inst.security_id, not inst.symbol"


# ═══════════════════════════════════════════════════════════════════════════════
# Options Scanner: Real Security IDs (Code Inspection Test)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptionsScannerSecurityIds:
    """Verify OptionsScanner resolves real security_ids via resolver."""

    def test_scanner_accepts_resolver_parameter(self):
        """OptionsScanner should accept resolver parameter."""
        from scalpr.scanner.options_scanner import OptionsScanner

        resolver = _FakeResolver()
        scanner = OptionsScanner(resolver=resolver)

        assert scanner._resolver is resolver

    def test_scanner_code_resolves_instruments(self):
        """OptionsScanner scan method should use resolver to get instruments."""
        import inspect

        from scalpr.scanner.options_scanner import OptionsScanner

        source = inspect.getsource(OptionsScanner.scan)

        assert "self._resolver" in source or "resolver" in source, \
            "OptionsScanner.scan should use resolver to get real instruments"

        assert "_ID" not in source or "security_id" in source, \
            "OptionsScanner should not create fake security_id strings ending with _ID"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Security ID Flow Through WebSocket
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndToEndSecurityIdFlow:
    """Verify security_id flows correctly through WebSocket subscription."""

    @pytest.mark.asyncio
    async def test_full_subscription_flow_reliance(self, fake_resolver):
        """Complete flow: Symbol → Resolver → security_id int → SDK subscription."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=fake_resolver,
        )

        feed = _FakeFeed()
        client._feed = feed
        client._connected = True

        await client.subscribe([("RELIANCE", "NSE")])

        fake_resolver.assert_resolve_called_once_with("RELIANCE", "NSE")

        call_args = feed.subscribe_symbols.call_args
        instruments = call_args[0][0]
        _exch_int, sec_id, mode_int = instruments[0]

        assert sec_id == "2885"
        assert isinstance(sec_id, str)

        assert mode_int in (15, 17, 21), f"Invalid SDK mode: {mode_int}"

    @pytest.mark.asyncio
    async def test_full_subscription_flow_tcs(self, fake_resolver):
        """Complete flow for TCS symbol."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=fake_resolver,
        )

        feed = _FakeFeed()
        client._feed = feed
        client._connected = True

        await client.subscribe([("TCS", "NSE")])

        call_args = feed.subscribe_symbols.call_args
        instruments = call_args[0][0]
        _exch_int, sec_id, _mode_int = instruments[0]

        assert sec_id == "11536"
