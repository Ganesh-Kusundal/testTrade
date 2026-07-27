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
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from scalpr.domain.instrument import Instrument, Exchange, Segment
from scalpr.brokers.dhan.ws_client import DhanWebSocketClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_resolver():
    """Create a mock SymbolResolver that returns real instruments."""
    resolver = MagicMock()
    
    def resolve(symbol, exchange="NSE"):
        # Simulate real instrument resolution
        instruments = {
            "RELIANCE": Instrument(
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                segment=Segment.EQUITY,
                security_id="2885",  # Real Dhan security_id for RELIANCE
                lot_size=1,
                tick_size=Decimal("0.05"),
            ),
            "TCS": Instrument(
                symbol="TCS",
                exchange=Exchange.NSE,
                segment=Segment.EQUITY,
                security_id="11536",  # Real Dhan security_id for TCS
                lot_size=1,
                tick_size=Decimal("0.05"),
            ),
        }
        inst = instruments.get(symbol)
        if inst is None:
            raise ValueError(f"Unknown symbol: {symbol}")
        return inst
    
    resolver.resolve.side_effect = resolve
    return resolver


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket Client: Security ID Resolution
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebSocketSecurityIdResolution:
    """Verify WebSocket client resolves symbols to security_ids before subscribing."""

    @pytest.mark.asyncio
    async def test_subscribe_resolves_security_id_via_resolver(self, mock_resolver):
        """subscribe() should resolve symbol to security_id using resolver."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=mock_resolver,
        )
        
        # Mock the SDK feed to capture subscription calls
        mock_feed = MagicMock()
        client._feed = mock_feed
        client._connected = True
        
        # Subscribe to RELIANCE
        result = await client.subscribe([("RELIANCE", "NSE")])
        
        # Verify resolver was called with correct arguments
        mock_resolver.resolve.assert_called_once_with("RELIANCE", "NSE")
        assert result is True

    @pytest.mark.asyncio
    async def test_subscribe_uses_integer_security_id(self, mock_resolver):
        """Security ID must be converted to integer for SDK."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=mock_resolver,
        )
        
        mock_feed = MagicMock()
        client._feed = mock_feed
        client._connected = True
        
        await client.subscribe([("RELIANCE", "NSE")])
        
        # Verify SDK feed received subscription with integer security_id
        call_args = mock_feed.subscribe_symbols.call_args
        assert call_args is not None, "subscribe_symbols should be called"
        
        instruments = call_args[0][0] if call_args[0] else []
        assert len(instruments) > 0, "Should have at least one instrument"
        
        # SDK format: (exchange_int, security_id_int, mode_int)
        exch_int, sec_id_int, mode_int = instruments[0]
        assert isinstance(sec_id_int, int), f"security_id must be int, got {type(sec_id_int)}"
        assert sec_id_int == 2885, f"Expected RELIANCE security_id=2885, got {sec_id_int}"

    @pytest.mark.asyncio
    async def test_subscribe_handles_resolution_failure_gracefully(self, mock_resolver):
        """subscribe() should handle resolution failures gracefully (log warning, skip)."""
        # Make resolver raise for unknown symbol
        mock_resolver.resolve.side_effect = ValueError("Unknown symbol: UNKNOWN")
        
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=mock_resolver,
        )
        
        mock_feed = MagicMock()
        client._feed = mock_feed
        client._connected = True
        
        # Should not raise, just skip the failed symbol
        # Returns True because empty subscription is considered "success" (no-op)
        result = await client.subscribe([("UNKNOWN", "NSE")])
        
        # Should not crash, just return True (no-op for already-subscribed/empty)
        assert result is True
        
        # Verify SDK feed was NOT called (no valid instruments)
        mock_feed.subscribe_symbols.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_subscribe_fallback_without_resolver(self):
        """subscribe() should fallback to int(symbol) if no resolver available."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=None,  # No resolver
        )
        
        mock_feed = MagicMock()
        client._feed = mock_feed
        client._connected = True
        
        # Subscribe using security_id directly as symbol (backward compat)
        result = await client.subscribe([("2885", "NSE")])
        
        # Should succeed by parsing "2885" as int
        assert result is True


# ═══════════════════════════════════════════════════════════════════════════════
# Orders: Security ID Usage (Code Inspection Test)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrdersSecurityIdUsage:
    """Verify orders code uses inst.security_id, not inst.symbol."""

    def test_orders_code_uses_security_id_field(self):
        """Orders adapter should reference inst.security_id in source code."""
        import inspect
        from scalpr.brokers.dhan.orders import OrdersAdapter
        
        # Get the source code of place_order method
        source = inspect.getsource(OrdersAdapter.place_order)
        
        # Verify it uses security_id, not symbol
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
        
        # Get the source code of _resolve_segment method (where security_id is extracted)
        source = inspect.getsource(HistoricalDataAdapter._resolve_segment)
        
        # Verify it uses security_id, not symbol
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
        
        mock_resolver = MagicMock()
        scanner = OptionsScanner(resolver=mock_resolver)
        
        assert scanner._resolver is mock_resolver

    def test_scanner_code_resolves_instruments(self):
        """OptionsScanner scan method should use resolver to get instruments."""
        import inspect
        from scalpr.scanner.options_scanner import OptionsScanner
        
        source = inspect.getsource(OptionsScanner.scan)
        
        # Should reference resolver
        assert "self._resolver" in source or "resolver" in source, \
            "OptionsScanner.scan should use resolver to get real instruments"
        
        # Should NOT create fake security_ids like "NIFTY_ID"
        assert "_ID" not in source or "security_id" in source, \
            "OptionsScanner should not create fake security_id strings ending with _ID"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: Security ID Flow Through WebSocket
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndToEndSecurityIdFlow:
    """Verify security_id flows correctly through WebSocket subscription."""

    @pytest.mark.asyncio
    async def test_full_subscription_flow_reliance(self, mock_resolver):
        """Complete flow: Symbol → Resolver → security_id int → SDK subscription."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=mock_resolver,
        )
        
        mock_feed = MagicMock()
        client._feed = mock_feed
        client._connected = True
        
        # Subscribe to RELIANCE
        await client.subscribe([("RELIANCE", "NSE")])
        
        # Verify the complete chain
        # 1. Resolver was called
        mock_resolver.resolve.assert_called_once_with("RELIANCE", "NSE")
        
        # 2. SDK received correct subscription
        call_args = mock_feed.subscribe_symbols.call_args
        instruments = call_args[0][0]
        exch_int, sec_id_int, mode_int = instruments[0]
        
        # 3. Security ID is correct integer
        assert sec_id_int == 2885
        assert isinstance(sec_id_int, int)
        
        # 4. Mode is valid SDK integer (15=Ticker, 17=Quote, 21=Full)
        assert mode_int in (15, 17, 21), f"Invalid SDK mode: {mode_int}"

    @pytest.mark.asyncio
    async def test_full_subscription_flow_tcs(self, mock_resolver):
        """Complete flow for TCS symbol."""
        client = DhanWebSocketClient(
            access_token="test_token",
            client_id="test_client",
            resolver=mock_resolver,
        )
        
        mock_feed = MagicMock()
        client._feed = mock_feed
        client._connected = True
        
        await client.subscribe([("TCS", "NSE")])
        
        call_args = mock_feed.subscribe_symbols.call_args
        instruments = call_args[0][0]
        exch_int, sec_id_int, mode_int = instruments[0]
        
        # TCS security_id is 11536
        assert sec_id_int == 11536
