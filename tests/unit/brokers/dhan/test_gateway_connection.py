"""Comprehensive unit tests for DhanConnection and DhanGateway.

Tests cover:
- Connection lifecycle (connect, disconnect, reconnect)
- Gateway delegation pattern (verify it calls connection methods)
- Config validation
- Adapter initialization
- Token refresh integration
- Error propagation
- BrokerPort interface compliance
- Thread safety
- State tracking
- Square-off logic
- Order mapping

Following Uncle Bob's principle: "Tests are first-class citizens.
Clean test code is production code."
Following Dr. Venkat's principle: "Test behaviour, not implementation.
A test name should state the expected behaviour under a condition."
"""

from __future__ import annotations

import threading
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.brokers.dhan.connection import DhanConnection
from scalpr.brokers.dhan.exceptions import (
    AuthenticationError,
    BrokerError,
    ConfigurationError,
)
from scalpr.brokers.dhan.gateway import DhanGateway
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position, PositionSide

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def valid_config():
    """Minimal valid config for DhanConnection."""
    return {
        "client_id": "test_client_123",
        "access_token": "test_token_abc",
    }


@pytest.fixture
def config_with_options(valid_config):
    """Config with all optional keys."""
    return {
        **valid_config,
        "base_url": "https://custom.api.dhan.co/v2",
        "timeout": 30.0,
        "token_refresh_fn": lambda: "new_token",
        "enable_retry": False,
        "instruments_force_refresh": True,
    }


@pytest.fixture
def sample_order():
    """A standard BUY LIMIT order."""
    return Order(
        order_id="ord_test_001",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        price=Decimal("2500.50"),
        state=OrderState.PENDING,
    )


@pytest.fixture
def sample_position_long():
    """A long position for testing."""
    return Position(
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        quantity=10,
        avg_price=Decimal("2500.00"),
        ltp=Decimal("2510.00"),
        unrealised_pnl=Decimal("100.00"),
        realised_pnl=Decimal("0"),
        position_side=PositionSide.LONG,
    )


@pytest.fixture
def sample_position_short():
    """A short position for testing."""
    return Position(
        symbol="TCS",
        exchange=Exchange.NSE,
        quantity=-5,
        avg_price=Decimal("3500.00"),
        ltp=Decimal("3480.00"),
        unrealised_pnl=Decimal("100.00"),
        realised_pnl=Decimal("0"),
        position_side=PositionSide.SHORT,
    )


@pytest.fixture
def sample_fill():
    """A standard execution fill."""
    return Fill(
        fill_id="fill_001",
        order_id="ord_test_001",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        price=Decimal("2500.50"),
    )


@pytest.fixture
def sample_raw_orderbook_entry():
    """Raw orderbook entry from Dhan API."""
    return {
        "order_id": "dhan_ord_12345",
        "symbol": "RELIANCE",
        "exchange_segment": "NSE_EQ",
        "side": "BUY",
        "order_type": "LIMIT",
        "status": "FILLED",
        "quantity": 10,
        "price": Decimal("2500.50"),
        "trigger_price": Decimal("0"),
        "filled_quantity": 10,
        "traded_price": Decimal("2500.50"),
        "product_type": "INTRADAY",
        "validity": "DAY",
        "reject_reason": "",
        "correlation_id": "corr_001",
    }


@pytest.fixture
def fully_mocked_connection():
    """Create a DhanConnection with all internal steps mocked for isolation."""
    with patch.object(DhanConnection, "_validate_config"), \
         patch.object(DhanConnection, "_create_http_client") as mock_client, \
         patch.object(DhanConnection, "_create_resolver") as mock_resolver, \
         patch.object(DhanConnection, "_verify_connection"):

        mock_http = MagicMock()
        mock_client.return_value = mock_http
        mock_resolver.return_value = MagicMock()

        conn = DhanConnection({"client_id": "c1", "access_token": "t1"})
        conn.connect()

        yield conn, mock_http, mock_resolver


@pytest.fixture
def mocked_gateway_connection():
    """Create a gateway with a fully mocked connection that is already 'connected'."""
    mock_conn = MagicMock()
    mock_conn.is_connected.return_value = True
    mock_conn.market_data = MagicMock()
    mock_conn.orders = MagicMock()
    mock_conn.portfolio = MagicMock()
    mock_conn.historical = MagicMock()

    with patch("scalpr.brokers.dhan.gateway.DhanConnection", return_value=mock_conn):
        gateway = DhanGateway({"client_id": "c1", "access_token": "t1"})
        yield gateway, mock_conn


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanConnection — Config Validation
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanConnectionConfigValidation:
    """Validate that DhanConnection rejects invalid configurations immediately."""

    def test_should_raise_configuration_error_when_client_id_missing(self):
        """Missing client_id should raise ConfigurationError at construction."""
        with pytest.raises(ConfigurationError, match="client_id"):
            DhanConnection({"access_token": "t1"})

    def test_should_raise_configuration_error_when_access_token_missing(self):
        """Missing access_token should raise ConfigurationError at construction."""
        with pytest.raises(ConfigurationError, match="access_token"):
            DhanConnection({"client_id": "c1"})

    def test_should_raise_configuration_error_when_both_required_keys_missing(self):
        """Empty config should report both missing keys."""
        with pytest.raises(ConfigurationError) as exc_info:
            DhanConnection({})

        assert "client_id" in str(exc_info.value)
        assert "access_token" in str(exc_info.value)

    def test_should_raise_configuration_error_when_client_id_is_empty_string(self):
        """Empty string client_id should be treated as missing."""
        with pytest.raises(ConfigurationError, match="client_id"):
            DhanConnection({"client_id": "", "access_token": "t1"})

    def test_should_raise_configuration_error_when_access_token_is_empty_string(self):
        """Empty string access_token should be treated as missing."""
        with pytest.raises(ConfigurationError, match="access_token"):
            DhanConnection({"client_id": "c1", "access_token": ""})

    def test_should_accept_valid_minimal_config(self, valid_config):
        """Minimal valid config with only required keys should not raise."""
        conn = DhanConnection(valid_config)
        assert conn is not None
        assert conn.is_connected() is False

    def test_should_accept_config_with_all_optional_keys(self, config_with_options):
        """Config with optional keys should be accepted without error."""
        conn = DhanConnection(config_with_options)
        assert conn is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanConnection — Connection Lifecycle
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanConnectionLifecycle:
    """Test the full connect → verify → disconnect lifecycle."""

    def test_should_create_http_client_on_connect(self, valid_config):
        """connect() must call _create_http_client exactly once."""
        with patch.object(DhanConnection, '_validate_config'), \
             patch.object(DhanConnection, '_create_http_client') as mock_client, \
             patch.object(DhanConnection, '_create_resolver') as mock_resolver, \
             patch.object(DhanConnection, '_verify_connection'):

            mock_http = MagicMock()
            mock_client.return_value = mock_http
            mock_resolver.return_value = MagicMock()

            conn = DhanConnection(valid_config)
            conn.connect()

            mock_client.assert_called_once()

    def test_should_load_instruments_on_connect(self, fully_mocked_connection):
        """connect() must call _create_resolver to load instrument master."""
        _conn, _, mock_resolver = fully_mocked_connection
        mock_resolver.assert_called_once()

    def test_should_verify_connection_via_profile_endpoint(self, fully_mocked_connection):
        """connect() must call _verify_connection after adapter init."""
        conn, _, _ = fully_mocked_connection
        with patch.object(conn, "_verify_connection", wraps=conn._verify_connection) as spy:
            conn.disconnect()
            conn.connect()
            spy.assert_called_once()

    def test_should_mark_connection_as_connected_after_successful_connect(self, fully_mocked_connection):
        """After connect() succeeds, is_connected() must return True."""
        conn, _, _ = fully_mocked_connection
        assert conn.is_connected() is True

    def test_should_start_as_not_connected(self, valid_config):
        """New connection must report is_connected() == False before connect()."""
        with patch.object(DhanConnection, "_validate_config"):
            conn = DhanConnection(valid_config)
            assert conn.is_connected() is False

    def test_should_be_idempotent_when_connect_called_twice(self, fully_mocked_connection):
        """Second connect() call must be a no-op, not reinitialise."""
        conn, mock_client, mock_resolver = fully_mocked_connection

        calls_before_client = mock_client.call_count
        calls_before_resolver = mock_resolver.call_count

        conn.connect()  # Second call — should be idempotent

        assert mock_client.call_count == calls_before_client
        assert mock_resolver.call_count == calls_before_resolver

    def test_should_cleanup_on_connect_failure(self, valid_config):
        """If _verify_connection fails, connection must clean up partial state."""
        with patch.object(DhanConnection, "_validate_config"), \
             patch.object(DhanConnection, "_create_http_client") as mock_client, \
             patch.object(DhanConnection, "_create_resolver") as mock_resolver, \
             patch.object(DhanConnection, "_verify_connection", side_effect=Exception("Network error")):

            mock_http = MagicMock()
            mock_client.return_value = mock_http
            mock_resolver.return_value = MagicMock()

            conn = DhanConnection(valid_config)

            with pytest.raises(BrokerError, match="Dhan connection failed"):
                conn.connect()

            assert conn.is_connected() is False
            # Verify cleanup cleared the http client
            mock_http.close.assert_called_once()

    def test_should_re_raise_authentication_error_without_wrapping(self, valid_config):
        """AuthenticationError must propagate directly, not wrapped in BrokerError."""
        with patch.object(DhanConnection, "_validate_config"), \
             patch.object(DhanConnection, "_create_http_client") as mock_client, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection", side_effect=AuthenticationError("Token expired")):

            mock_http = MagicMock()
            mock_client.return_value = mock_http

            conn = DhanConnection(valid_config)

            with pytest.raises(AuthenticationError, match="Token expired"):
                conn.connect()

            assert conn.is_connected() is False

    def test_should_disconnect_clear_all_adapters(self, fully_mocked_connection):
        """disconnect() must set _connected to False and clear adapters."""
        conn, mock_http, _ = fully_mocked_connection

        conn.disconnect()

        assert conn.is_connected() is False
        mock_http.close.assert_called_once()

    def test_should_be_safe_to_disconnect_when_already_disconnected(self, fully_mocked_connection):
        """Calling disconnect() on an already disconnected connection must not raise."""
        conn, mock_http, _ = fully_mocked_connection
        conn.disconnect()
        conn.disconnect()  # Second call — must be safe
        mock_http.close.assert_called_once()  # close() called only once


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanConnection — Adapter Properties
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanConnectionAdapterProperties:
    """Verify adapter properties raise BrokerError when accessed before connect()."""

    def test_should_raise_broker_error_when_market_data_accessed_before_connect(self, valid_config):
        """Accessing .market_data before connect() must raise BrokerError."""
        with patch.object(DhanConnection, "_validate_config"):
            conn = DhanConnection(valid_config)
            with pytest.raises(BrokerError, match="Market data adapter not initialised"):
                _ = conn.market_data

    def test_should_raise_broker_error_when_orders_accessed_before_connect(self, valid_config):
        """Accessing .orders before connect() must raise BrokerError."""
        with patch.object(DhanConnection, "_validate_config"):
            conn = DhanConnection(valid_config)
            with pytest.raises(BrokerError, match="Orders adapter not initialised"):
                _ = conn.orders

    def test_should_raise_broker_error_when_portfolio_accessed_before_connect(self, valid_config):
        """Accessing .portfolio before connect() must raise BrokerError."""
        with patch.object(DhanConnection, "_validate_config"):
            conn = DhanConnection(valid_config)
            with pytest.raises(BrokerError, match="Portfolio adapter not initialised"):
                _ = conn.portfolio

    def test_should_raise_broker_error_when_historical_accessed_before_connect(self, valid_config):
        """Accessing .historical before connect() must raise BrokerError."""
        with patch.object(DhanConnection, "_validate_config"):
            conn = DhanConnection(valid_config)
            with pytest.raises(BrokerError, match="Historical data adapter not initialised"):
                _ = conn.historical

    def test_should_raise_broker_error_when_resolver_accessed_before_connect(self, valid_config):
        """Accessing .resolver before connect() must raise BrokerError."""
        with patch.object(DhanConnection, "_validate_config"):
            conn = DhanConnection(valid_config)
            with pytest.raises(BrokerError, match="Symbol resolver not initialised"):
                _ = conn.resolver

    def test_should_raise_broker_error_when_http_client_accessed_before_connect(self, valid_config):
        """Accessing .http_client before connect() must raise BrokerError."""
        with patch.object(DhanConnection, "_validate_config"):
            conn = DhanConnection(valid_config)
            with pytest.raises(BrokerError, match="HTTP client not initialised"):
                _ = conn.http_client

    def test_should_return_adapters_after_connect(self, fully_mocked_connection):
        """After connect(), all adapter properties must return non-None."""
        conn, _, _ = fully_mocked_connection

        assert conn.market_data is not None
        assert conn.orders is not None
        assert conn.portfolio is not None
        assert conn.historical is not None
        assert conn.resolver is not None
        assert conn.http_client is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanConnection — Thread Safety
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanConnectionThreadSafety:
    """Verify that concurrent connect/disconnect calls are handled safely."""

    def test_should_handle_concurrent_connect_calls_safely(self, valid_config):
        """Multiple threads calling connect() simultaneously must not corrupt state."""
        with patch.object(DhanConnection, "_validate_config"), \
             patch.object(DhanConnection, "_create_http_client") as mock_client, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            mock_http = MagicMock()
            mock_client.return_value = mock_http

            conn = DhanConnection(valid_config)
            errors = []

            def try_connect():
                try:
                    conn.connect()
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=try_connect) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
            assert conn.is_connected() is True

    def test_should_handle_concurrent_disconnect_calls_safely(self, fully_mocked_connection):
        """Multiple threads calling disconnect() simultaneously must not raise."""
        conn, _, _ = fully_mocked_connection
        errors = []

        def try_disconnect():
            try:
                conn.disconnect()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=try_disconnect) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert conn.is_connected() is False

    def test_should_handle_rapid_connect_disconnect_cycles(self, valid_config):
        """Rapid connect → disconnect cycles must not leave inconsistent state."""
        with patch.object(DhanConnection, "_validate_config"), \
             patch.object(DhanConnection, "_create_http_client") as mock_client, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            mock_http = MagicMock()
            mock_client.return_value = mock_http

            conn = DhanConnection(valid_config)

            for _ in range(5):
                conn.connect()
                assert conn.is_connected() is True
                conn.disconnect()
                assert conn.is_connected() is False


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanConnection — Connection State Tracking
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanConnectionStateTracking:
    """Verify accurate connection state reporting throughout the lifecycle."""

    def test_should_report_disconnected_before_connect(self, valid_config):
        """Initial state must be disconnected."""
        with patch.object(DhanConnection, "_validate_config"):
            conn = DhanConnection(valid_config)
            assert conn.is_connected() is False

    def test_should_report_connected_after_successful_connect(self, fully_mocked_connection):
        """After successful connect, state must be connected."""
        conn, _, _ = fully_mocked_connection
        assert conn.is_connected() is True

    def test_should_report_disconnected_after_disconnect(self, fully_mocked_connection):
        """After disconnect, state must be disconnected."""
        conn, _, _ = fully_mocked_connection
        conn.disconnect()
        assert conn.is_connected() is False

    def test_should_report_disconnected_after_failed_connect(self, valid_config):
        """After a failed connect attempt, state must remain disconnected."""
        with patch.object(DhanConnection, "_validate_config"), \
             patch.object(DhanConnection, "_create_http_client") as mock_client, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection", side_effect=Exception("fail")):

            mock_http = MagicMock()
            mock_client.return_value = mock_http

            conn = DhanConnection(valid_config)
            with pytest.raises(BrokerError):
                conn.connect()

            assert conn.is_connected() is False


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanConnection — Token Refresh Integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanConnectionTokenRefresh:
    """Verify token_refresh_fn is passed through to the HTTP client."""

    def test_should_pass_token_refresh_fn_to_http_client(self, valid_config):
        """token_refresh_fn from config must be passed to DhanHttpClient."""
        refresh_fn = MagicMock(return_value="new_token_xyz")
        config = {**valid_config, "token_refresh_fn": refresh_fn}

        with patch("scalpr.brokers.dhan.connection.DhanHttpClient") as MockHttpClient, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            MockHttpClient.return_value = MagicMock()
            conn = DhanConnection(config)
            conn.connect()

            MockHttpClient.assert_called_once()
            call_kwargs = MockHttpClient.call_args[1]
            assert call_kwargs["token_refresh_fn"] is refresh_fn

    def test_should_handle_none_token_refresh_fn_gracefully(self, valid_config):
        """Missing token_refresh_fn must not cause errors."""
        with patch("scalpr.brokers.dhan.connection.DhanHttpClient") as MockHttpClient, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            MockHttpClient.return_value = MagicMock()
            conn = DhanConnection(valid_config)
            conn.connect()

            call_kwargs = MockHttpClient.call_args[1]
            assert call_kwargs["token_refresh_fn"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanConnection — HTTP Client Configuration
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanConnectionHttpClientConfig:
    """Verify HTTP client is configured with the correct parameters."""

    def test_should_use_default_base_url_when_not_specified(self, valid_config):
        """When base_url is missing, Dhan.REST_BASE must be used."""
        with patch("scalpr.brokers.dhan.connection.DhanHttpClient") as MockHttpClient, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            from config.endpoints import Dhan
            MockHttpClient.return_value = MagicMock()

            conn = DhanConnection(valid_config)
            conn.connect()

            call_kwargs = MockHttpClient.call_args[1]
            assert call_kwargs["base_url"] == Dhan.REST_BASE

    def test_should_use_custom_base_url_when_specified(self, config_with_options):
        """Custom base_url from config must override the default."""
        with patch("scalpr.brokers.dhan.connection.DhanHttpClient") as MockHttpClient, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            MockHttpClient.return_value = MagicMock()

            conn = DhanConnection(config_with_options)
            conn.connect()

            call_kwargs = MockHttpClient.call_args[1]
            assert call_kwargs["base_url"] == "https://custom.api.dhan.co/v2"

    def test_should_use_default_timeout_when_not_specified(self, valid_config):
        """Default timeout must be 15.0 seconds."""
        with patch("scalpr.brokers.dhan.connection.DhanHttpClient") as MockHttpClient, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            MockHttpClient.return_value = MagicMock()

            conn = DhanConnection(valid_config)
            conn.connect()

            call_kwargs = MockHttpClient.call_args[1]
            assert call_kwargs["timeout"] == 15.0

    def test_should_use_custom_timeout_when_specified(self, config_with_options):
        """Custom timeout from config must be used."""
        with patch("scalpr.brokers.dhan.connection.DhanHttpClient") as MockHttpClient, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            MockHttpClient.return_value = MagicMock()

            conn = DhanConnection(config_with_options)
            conn.connect()

            call_kwargs = MockHttpClient.call_args[1]
            assert call_kwargs["timeout"] == 30.0

    def test_should_use_default_enable_retry_when_not_specified(self, valid_config):
        """Default enable_retry must be True."""
        with patch("scalpr.brokers.dhan.connection.DhanHttpClient") as MockHttpClient, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            MockHttpClient.return_value = MagicMock()

            conn = DhanConnection(valid_config)
            conn.connect()

            call_kwargs = MockHttpClient.call_args[1]
            assert call_kwargs["enable_retry"] is True

    def test_should_pass_enable_retry_false_when_specified(self, config_with_options):
        """enable_retry=False must be passed through."""
        with patch("scalpr.brokers.dhan.connection.DhanHttpClient") as MockHttpClient, \
             patch.object(DhanConnection, "_create_resolver"), \
             patch.object(DhanConnection, "_verify_connection"):

            MockHttpClient.return_value = MagicMock()

            conn = DhanConnection(config_with_options)
            conn.connect()

            call_kwargs = MockHttpClient.call_args[1]
            assert call_kwargs["enable_retry"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Interface Compliance
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayInterfaceCompliance:
    """Verify DhanGateway correctly implements the IBrokerGateway contract."""

    def test_should_implement_ibrokergateway_interface(self):
        """DhanGateway must be a subclass of IBrokerGateway."""
        assert issubclass(DhanGateway, IBrokerGateway)

    def test_should_implement_all_abstract_methods(self):
        """All IBrokerGateway abstract methods must be implemented."""
        abstract_methods = set()
        for cls in IBrokerGateway.__mro__:
            for name, method in vars(cls).items():
                if getattr(method, "__isabstractmethod__", False):
                    abstract_methods.add(name)

        concrete_methods = set()
        for name, method in vars(DhanGateway).items():
            if callable(method) and not name.startswith("_"):
                concrete_methods.add(name)

        missing = abstract_methods - concrete_methods
        assert not missing, f"Missing implementations: {missing}"

    def test_should_instantiate_with_valid_config(self, valid_config):
        """DhanGateway must construct without error with valid config."""
        with patch("scalpr.brokers.dhan.gateway.DhanConnection"):
            gateway = DhanGateway(valid_config)
            assert gateway is not None

    def test_should_create_dhan_connection_with_config(self, valid_config):
        """DhanGateway must create a DhanConnection with the provided config."""
        with patch("scalpr.brokers.dhan.gateway.DhanConnection") as MockConnection:
            DhanGateway(valid_config)
            MockConnection.assert_called_once_with(valid_config)


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Lifecycle Delegation
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayLifecycleDelegation:
    """Verify gateway correctly delegates lifecycle methods to connection."""

    def test_should_delegate_connect_to_connection(self, mocked_gateway_connection):
        """gateway.connect() must call connection.connect()."""
        gateway, mock_conn = mocked_gateway_connection
        gateway.connect()
        mock_conn.connect.assert_called_once()

    def test_should_delegate_disconnect_to_connection(self, mocked_gateway_connection):
        """gateway.disconnect() must call connection.disconnect()."""
        gateway, mock_conn = mocked_gateway_connection
        gateway.disconnect()
        mock_conn.disconnect.assert_called_once()

    def test_should_delegate_is_connected_to_connection(self, mocked_gateway_connection):
        """gateway.is_connected() must call connection.is_connected()."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.is_connected.return_value = True
        result = gateway.is_connected()
        assert result is True
        mock_conn.is_connected.assert_called_once()

    def test_should_return_false_when_connection_reports_disconnected(self, mocked_gateway_connection):
        """gateway.is_connected() must return False when connection is disconnected."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.is_connected.return_value = False
        result = gateway.is_connected()
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Market Data Delegation
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayMarketDataDelegation:
    """Verify gateway correctly delegates market data methods to connection adapters."""

    def test_should_delegate_get_ltp_to_market_data_adapter(self, mocked_gateway_connection):
        """gateway.get_ltp() must call connection.market_data.get_ltp()."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.market_data.get_ltp.return_value = Decimal("2500.50")
        result = gateway.get_ltp("RELIANCE", "NSE")
        assert result == Decimal("2500.50")
        mock_conn.market_data.get_ltp.assert_called_once_with("RELIANCE", "NSE")

    def test_should_delegate_get_quote_to_market_data_adapter(self, mocked_gateway_connection):
        """gateway.get_quote() must call connection.market_data.get_quote()."""
        gateway, mock_conn = mocked_gateway_connection
        expected_quote = {"ltp": Decimal("2500.50"), "volume": 1000}
        mock_conn.market_data.get_quote.return_value = expected_quote
        result = gateway.get_quote("RELIANCE", "NSE")
        assert result == expected_quote
        mock_conn.market_data.get_quote.assert_called_once_with("RELIANCE", "NSE")


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Order Operations Delegation
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayOrderDelegation:
    """Verify gateway correctly delegates order operations to connection adapters."""

    def test_should_delegate_place_order_to_orders_adapter(self, mocked_gateway_connection, sample_order, sample_fill):
        """gateway.place_order() must call connection.orders.place_order()."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.place_order.return_value = sample_fill
        result = gateway.place_order(sample_order)
        assert result is sample_fill
        mock_conn.orders.place_order.assert_called_once_with(sample_order)

    def test_should_delegate_modify_order_to_orders_adapter(self, mocked_gateway_connection):
        """gateway.modify_order() must call connection.orders.modify_order()."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.modify_order.return_value = True
        result = gateway.modify_order("ord_123", Decimal("2600.00"), 20)
        assert result is True
        mock_conn.orders.modify_order.assert_called_once_with(
            "ord_123", Decimal("2600.00"), 20, None
        )

    def test_should_delegate_modify_order_with_trigger_price(self, mocked_gateway_connection):
        """gateway.modify_order() with trigger_price must pass it through."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.modify_order.return_value = True
        result = gateway.modify_order(
            "ord_123", Decimal("2600.00"), 20, Decimal("2550.00")
        )
        assert result is True
        mock_conn.orders.modify_order.assert_called_once_with(
            "ord_123", Decimal("2600.00"), 20, Decimal("2550.00")
        )

    def test_should_delegate_cancel_order_to_orders_adapter(self, mocked_gateway_connection):
        """gateway.cancel_order() must call connection.orders.cancel_order()."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.cancel_order.return_value = True
        result = gateway.cancel_order("ord_123")
        assert result is True
        mock_conn.orders.cancel_order.assert_called_once_with("ord_123")


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Portfolio Delegation
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayPortfolioDelegation:
    """Verify gateway correctly delegates portfolio methods to connection adapters."""

    def test_should_delegate_get_positions_to_portfolio_adapter(self, mocked_gateway_connection, sample_position_long):
        """gateway.get_positions() must call connection.portfolio.get_positions()."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.portfolio.get_positions.return_value = [sample_position_long]
        result = gateway.get_positions()
        assert result == [sample_position_long]
        mock_conn.portfolio.get_positions.assert_called_once()

    def test_should_delegate_get_holdings_to_portfolio_adapter(self, mocked_gateway_connection):
        """gateway.get_holdings() must call connection.portfolio.get_holdings()."""
        gateway, mock_conn = mocked_gateway_connection
        expected_holdings = [MagicMock(spec=Position)]
        mock_conn.portfolio.get_holdings.return_value = expected_holdings
        result = gateway.get_holdings()
        assert result == expected_holdings
        mock_conn.portfolio.get_holdings.assert_called_once()

    def test_should_delegate_get_margins_to_portfolio_adapter(self, mocked_gateway_connection):
        """gateway.get_margins() must call connection.portfolio.get_fund_limits()."""
        gateway, mock_conn = mocked_gateway_connection
        expected_margins = {
            "available_margin": Decimal("50000"),
            "used_margin": Decimal("10000"),
            "total_balance": Decimal("60000"),
        }
        mock_conn.portfolio.get_fund_limits.return_value = expected_margins
        result = gateway.get_margins()
        assert result == expected_margins
        mock_conn.portfolio.get_fund_limits.assert_called_once()

    def test_should_delegate_get_fund_limits_to_get_margins(self, mocked_gateway_connection):
        """gateway.get_fund_limits() must call gateway.get_margins()."""
        gateway, mock_conn = mocked_gateway_connection
        expected_margins = {"available_margin": Decimal("50000")}
        mock_conn.portfolio.get_fund_limits.return_value = expected_margins
        result = gateway.get_fund_limits()
        assert result == expected_margins


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Historical Data Delegation
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayHistoricalDelegation:
    """Verify gateway correctly delegates historical data to connection adapter."""

    def test_should_delegate_get_ohlcv_to_historical_adapter(self, mocked_gateway_connection):
        """gateway.get_ohlcv() must call connection.historical.get_ohlcv()."""
        gateway, mock_conn = mocked_gateway_connection
        expected_candles = [
            {"timestamp": "2024-01-01", "open": Decimal("100"), "close": Decimal("101")},
        ]
        mock_conn.historical.get_ohlcv.return_value = expected_candles
        result = gateway.get_ohlcv(
            "RELIANCE", "NSE", "1D", date(2024, 1, 1), date(2024, 1, 31)
        )
        assert result == expected_candles
        mock_conn.historical.get_ohlcv.assert_called_once_with(
            "RELIANCE", "NSE", "1D", date(2024, 1, 1), date(2024, 1, 31)
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Square Off Logic
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewaySquareOff:
    """Verify square_off_all correctly closes positions with counter market orders."""

    def test_should_sell_for_long_positions(self, mocked_gateway_connection, sample_position_long, sample_fill):
        """Long positions must be closed with SELL market orders."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.portfolio.get_positions.return_value = [sample_position_long]
        mock_conn.orders.place_order.return_value = sample_fill

        fills = gateway.square_off_all()

        assert len(fills) == 1
        placed_order = mock_conn.orders.place_order.call_args[0][0]
        assert placed_order.side == OrderSide.SELL
        assert placed_order.order_type == OrderType.MARKET
        assert placed_order.quantity == 10

    def test_should_buy_for_short_positions(self, mocked_gateway_connection, sample_position_short, sample_fill):
        """Short positions must be closed with BUY market orders."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.portfolio.get_positions.return_value = [sample_position_short]
        mock_conn.orders.place_order.return_value = sample_fill

        fills = gateway.square_off_all()

        assert len(fills) == 1
        placed_order = mock_conn.orders.place_order.call_args[0][0]
        assert placed_order.side == OrderSide.BUY
        assert placed_order.order_type == OrderType.MARKET
        assert placed_order.quantity == 5

    def test_should_skip_zero_quantity_positions(self, mocked_gateway_connection, sample_fill):
        """Positions with quantity=0 must be skipped."""
        gateway, mock_conn = mocked_gateway_connection
        flat_position = Position(
            symbol="INFY",
            exchange=Exchange.NSE,
            quantity=0,
            avg_price=Decimal("1500"),
            ltp=Decimal("1505"),
        )
        mock_conn.portfolio.get_positions.return_value = [flat_position]
        mock_conn.orders.place_order.return_value = sample_fill

        fills = gateway.square_off_all()

        assert len(fills) == 0
        mock_conn.orders.place_order.assert_not_called()

    def test_should_square_off_multiple_positions(self, mocked_gateway_connection, sample_position_long, sample_position_short, sample_fill):
        """All open positions must be squared off."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.portfolio.get_positions.return_value = [sample_position_long, sample_position_short]
        mock_conn.orders.place_order.return_value = sample_fill

        fills = gateway.square_off_all()

        assert len(fills) == 2
        assert mock_conn.orders.place_order.call_count == 2

    def test_should_re_raise_broker_error_on_square_off_failure(self, mocked_gateway_connection, sample_position_long):
        """If place_order fails during square_off, BrokerError must be raised."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.portfolio.get_positions.return_value = [sample_position_long]
        mock_conn.orders.place_order.side_effect = Exception("API timeout")

        with pytest.raises(BrokerError, match="Square-off failed"):
            gateway.square_off_all()

    def test_should_use_ltp_as_price_when_available(self, mocked_gateway_connection, sample_fill):
        """Square-off order must use position LTP as price when LTP > 0."""
        gateway, mock_conn = mocked_gateway_connection
        position_with_ltp = Position(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            quantity=10,
            avg_price=Decimal("2500"),
            ltp=Decimal("2510"),
        )
        mock_conn.portfolio.get_positions.return_value = [position_with_ltp]
        mock_conn.orders.place_order.return_value = sample_fill

        gateway.square_off_all()

        placed_order = mock_conn.orders.place_order.call_args[0][0]
        assert placed_order.price == Decimal("2510")

    def test_should_use_zero_price_when_ltp_is_zero(self, mocked_gateway_connection, sample_fill):
        """Square-off order must use price=0 when position LTP is 0."""
        gateway, mock_conn = mocked_gateway_connection
        position_no_ltp = Position(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            quantity=10,
            avg_price=Decimal("2500"),
            ltp=Decimal("0"),
        )
        mock_conn.portfolio.get_positions.return_value = [position_no_ltp]
        mock_conn.orders.place_order.return_value = sample_fill

        gateway.square_off_all()

        placed_order = mock_conn.orders.place_order.call_args[0][0]
        assert placed_order.price == Decimal("0")


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Order Mapping
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayOrderMapping:
    """Verify _map_raw_order_to_order correctly maps Dhan responses to domain objects."""

    def test_should_map_filled_buy_limit_order(self, sample_raw_orderbook_entry):
        """A filled BUY LIMIT order must map to OrderState.FILLED and OrderSide.BUY."""
        order = DhanGateway._map_raw_order_to_order(sample_raw_orderbook_entry)

        assert order.order_id == "dhan_ord_12345"
        assert order.symbol == "RELIANCE"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.state == OrderState.FILLED
        assert order.quantity == 10
        assert order.price == Decimal("2500.50")
        assert order.filled_quantity == 10
        assert order.avg_price == Decimal("2500.50")

    def test_should_map_sell_market_order(self):
        """A SELL MARKET order must map correctly."""
        raw = {
            "order_id": "ord_sell",
            "symbol": "TCS",
            "exchange_segment": "NSE_EQ",
            "side": "SELL",
            "order_type": "MARKET",
            "status": "FILLED",
            "quantity": 5,
            "price": Decimal("0"),
            "trigger_price": Decimal("0"),
            "filled_quantity": 5,
            "traded_price": Decimal("3500.00"),
            "product_type": "DELIVERY",
            "validity": "DAY",
        }
        order = DhanGateway._map_raw_order_to_order(raw)

        assert order.side == OrderSide.SELL
        assert order.order_type == OrderType.MARKET
        assert order.avg_price == Decimal("3500.00")

    def test_should_map_sl_order_to_stop_loss(self):
        """Dhan 'SL' order type must map to OrderType.STOP_LOSS."""
        raw = {
            "order_id": "ord_sl",
            "symbol": "INFY",
            "exchange_segment": "NSE_EQ",
            "side": "BUY",
            "order_type": "SL",
            "status": "OPEN",
            "quantity": 10,
            "price": Decimal("1500"),
            "trigger_price": Decimal("1490"),
        }
        order = DhanGateway._map_raw_order_to_order(raw)

        assert order.order_type == OrderType.STOP_LOSS

    def test_should_map_slm_order_to_stop_loss_market(self):
        """Dhan 'SL-M' order type must map to OrderType.STOP_LOSS_MARKET."""
        raw = {
            "order_id": "ord_slm",
            "symbol": "INFY",
            "exchange_segment": "NSE_EQ",
            "side": "BUY",
            "order_type": "SL-M",
            "status": "OPEN",
            "quantity": 10,
            "price": Decimal("0"),
            "trigger_price": Decimal("1490"),
        }
        order = DhanGateway._map_raw_order_to_order(raw)

        assert order.order_type == OrderType.STOP_LOSS_MARKET

    def test_should_map_stop_loss_full_name_to_stop_loss(self):
        """Dhan 'STOP LOSS' order type must map to OrderType.STOP_LOSS."""
        raw = {
            "order_id": "ord_sl",
            "symbol": "INFY",
            "exchange_segment": "NSE_EQ",
            "side": "BUY",
            "order_type": "STOP LOSS",
            "status": "OPEN",
        }
        order = DhanGateway._map_raw_order_to_order(raw)
        assert order.order_type == OrderType.STOP_LOSS

    def test_should_map_stop_loss_market_full_name(self):
        """Dhan 'STOP LOSS MARKET' must map to OrderType.STOP_LOSS_MARKET."""
        raw = {
            "order_id": "ord_slm",
            "symbol": "INFY",
            "exchange_segment": "NSE_EQ",
            "side": "BUY",
            "order_type": "STOP LOSS MARKET",
            "status": "OPEN",
        }
        order = DhanGateway._map_raw_order_to_order(raw)
        assert order.order_type == OrderType.STOP_LOSS_MARKET

    def test_should_map_mcx_exchange(self):
        """MCX exchange segment must map to Exchange.MCX."""
        raw = {
            "order_id": "ord_mcx",
            "symbol": "GOLD",
            "exchange_segment": "MCX_COMM",
            "side": "BUY",
            "order_type": "LIMIT",
            "status": "OPEN",
            "price": Decimal("50000"),
        }
        order = DhanGateway._map_raw_order_to_order(raw)
        assert order.exchange == Exchange.MCX

    def test_should_default_to_nse_exchange(self):
        """Unknown exchange segment must default to Exchange.NSE."""
        raw = {
            "order_id": "ord_unknown",
            "symbol": "UNKNOWN",
            "exchange_segment": "UNKNOWN_EXCHANGE",
            "side": "BUY",
            "order_type": "LIMIT",
            "status": "OPEN",
            "price": Decimal("100"),
        }
        order = DhanGateway._map_raw_order_to_order(raw)
        assert order.exchange == Exchange.NSE

    def test_should_map_all_order_states(self):
        """All Dhan status strings must map to correct OrderState."""
        status_mapping = {
            "PENDING": OrderState.PENDING,
            "OPEN": OrderState.OPEN,
            "PARTIALLY FILLED": OrderState.PARTIALLY_FILLED,
            "FILLED": OrderState.FILLED,
            "CANCELLED": OrderState.CANCELLED,
            "REJECTED": OrderState.REJECTED,
            "EXPIRED": OrderState.EXPIRED,
            "TRIGGER PENDING": OrderState.PENDING,
        }

        for status_str, expected_state in status_mapping.items():
            raw = {
                "order_id": "ord_test",
                "symbol": "RELIANCE",
                "exchange_segment": "NSE_EQ",
                "side": "BUY",
                "order_type": "MARKET",
                "status": status_str,
            }
            order = DhanGateway._map_raw_order_to_order(raw)
            assert order.state == expected_state, f"Failed for status: {status_str}"

    def test_should_default_to_pending_for_unknown_status(self):
        """Unknown status string must default to OrderState.PENDING."""
        raw = {
            "order_id": "ord_test",
            "symbol": "RELIANCE",
            "exchange_segment": "NSE_EQ",
            "side": "BUY",
            "order_type": "MARKET",
            "status": "UNKNOWN_STATUS",
        }
        order = DhanGateway._map_raw_order_to_order(raw)
        assert order.state == OrderState.PENDING

    def test_should_default_to_limit_for_unknown_order_type(self):
        """Unknown order type must default to OrderType.LIMIT."""
        raw = {
            "order_id": "ord_test",
            "symbol": "RELIANCE",
            "exchange_segment": "NSE_EQ",
            "side": "BUY",
            "order_type": "UNKNOWN_TYPE",
            "status": "OPEN",
            "price": Decimal("100"),
        }
        order = DhanGateway._map_raw_order_to_order(raw)
        assert order.order_type == OrderType.LIMIT

    def test_should_map_reject_reason(self, sample_raw_orderbook_entry):
        """Reject reason must be mapped from raw data."""
        raw = {**sample_raw_orderbook_entry, "reject_reason": "Insufficient margin"}
        order = DhanGateway._map_raw_order_to_order(raw)
        assert order.reject_reason == "Insufficient margin"

    def test_should_map_correlation_id(self, sample_raw_orderbook_entry):
        """Correlation ID must be mapped from raw data."""
        raw = {**sample_raw_orderbook_entry, "correlation_id": "corr_999"}
        order = DhanGateway._map_raw_order_to_order(raw)
        assert order.correlation_id == "corr_999"

    def test_should_handle_missing_optional_fields(self):
        """Missing optional fields must use sensible defaults."""
        raw = {
            "order_id": "ord_minimal",
            "symbol": "RELIANCE",
            "exchange_segment": "NSE_EQ",
            "side": "BUY",
            "order_type": "MARKET",
            "status": "OPEN",
        }
        order = DhanGateway._map_raw_order_to_order(raw)

        assert order.order_id == "ord_minimal"
        assert order.quantity == 0
        assert order.price == Decimal("0")
        assert order.trigger_price == Decimal("0")
        assert order.filled_quantity == 0
        assert order.avg_price == Decimal("0")
        assert order.reject_reason == ""
        assert order.correlation_id is None


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Error Propagation
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayErrorPropagation:
    """Verify errors from connection/adapters propagate correctly through the gateway."""

    def test_should_propagate_broker_error_from_place_order(self, mocked_gateway_connection, sample_order):
        """BrokerError from orders adapter must propagate through gateway."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.place_order.side_effect = BrokerError("API error: invalid token")
        with pytest.raises(BrokerError, match="API error: invalid token"):
            gateway.place_order(sample_order)

    def test_should_propagate_broker_error_from_cancel_order(self, mocked_gateway_connection):
        """BrokerError from cancel_order must propagate."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.cancel_order.side_effect = BrokerError("Order already cancelled")
        with pytest.raises(BrokerError, match="Order already cancelled"):
            gateway.cancel_order("ord_123")

    def test_should_propagate_broker_error_from_get_positions(self, mocked_gateway_connection):
        """BrokerError from get_positions must propagate."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.portfolio.get_positions.side_effect = BrokerError("Portfolio fetch failed")
        with pytest.raises(BrokerError, match="Portfolio fetch failed"):
            gateway.get_positions()

    def test_should_raise_broker_error_when_get_order_status_order_not_found(self, mocked_gateway_connection):
        """get_order_status must raise BrokerError when order_id not found."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.get_orderbook.return_value = [
            {"order_id": "other_order", "status": "OPEN"},
        ]
        with pytest.raises(BrokerError, match="Order not found in orderbook"):
            gateway.get_order_status("ord_missing")

    def test_should_return_order_when_get_order_status_finds_match(self, mocked_gateway_connection, sample_raw_orderbook_entry):
        """get_order_status must return mapped Order when order_id is found."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.get_orderbook.return_value = [sample_raw_orderbook_entry]
        order = gateway.get_order_status("dhan_ord_12345")
        assert order.order_id == "dhan_ord_12345"
        assert order.state == OrderState.FILLED


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Full Delegation Chain
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayFullDelegationChain:
    """Integration-style tests verifying the full delegation chain: gateway → connection → adapter."""

    def test_should_execute_full_place_order_chain(self, mocked_gateway_connection, sample_order, sample_fill):
        """Verify: gateway.place_order → connection.orders.place_order → returns Fill."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.place_order.return_value = sample_fill

        # Full chain
        gateway.connect()
        fill = gateway.place_order(sample_order)
        gateway.disconnect()

        assert fill is sample_fill
        mock_conn.connect.assert_called_once()
        mock_conn.orders.place_order.assert_called_once_with(sample_order)
        mock_conn.disconnect.assert_called_once()

    def test_should_execute_full_get_positions_chain(self, mocked_gateway_connection, sample_position_long):
        """Verify: gateway.get_positions → connection.portfolio.get_positions → returns list[Position]."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.portfolio.get_positions.return_value = [sample_position_long]
        gateway.connect()

        positions = gateway.get_positions()

        assert len(positions) == 1
        assert positions[0].symbol == "RELIANCE"
        assert positions[0].quantity == 10
        mock_conn.portfolio.get_positions.assert_called_once()

    def test_should_execute_full_square_off_chain(self, mocked_gateway_connection, sample_position_long, sample_fill):
        """Verify: gateway.square_off_all → get_positions → place_order → returns fills."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.portfolio.get_positions.return_value = [sample_position_long]
        mock_conn.orders.place_order.return_value = sample_fill

        gateway.connect()

        fills = gateway.square_off_all()

        assert len(fills) == 1
        # Verify the order placed was a SELL market order for the position quantity
        placed_order = mock_conn.orders.place_order.call_args[0][0]
        assert placed_order.side == OrderSide.SELL
        assert placed_order.order_type == OrderType.MARKET
        assert placed_order.quantity == 10
        assert placed_order.symbol == "RELIANCE"

    def test_should_execute_full_lifecycle(self, mocked_gateway_connection, sample_order, sample_fill, sample_position_long):
        """Verify complete lifecycle: connect → trade → check position → square off → disconnect."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.orders.place_order.return_value = sample_fill
        mock_conn.portfolio.get_positions.return_value = [sample_position_long]

        # Connect
        gateway.connect()
        assert gateway.is_connected() is True

        # Place order
        fill = gateway.place_order(sample_order)
        assert fill is sample_fill

        # Check positions
        positions = gateway.get_positions()
        assert len(positions) == 1

        # Square off
        fills = gateway.square_off_all()
        assert len(fills) == 1

        # Disconnect - mock must return False after disconnect
        def side_effect_is_connected():
            # After disconnect is called, return False
            return not mock_conn.disconnect.called
        mock_conn.is_connected.side_effect = side_effect_is_connected

        gateway.disconnect()
        assert gateway.is_connected() is False

        # Verify call sequence
        mock_conn.connect.assert_called_once()
        mock_conn.orders.place_order.assert_called()
        mock_conn.portfolio.get_positions.assert_called()
        mock_conn.disconnect.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# TestDhanGateway — Connection Property Access
# ═══════════════════════════════════════════════════════════════════════════════


class TestDhanGatewayConnectionProperty:
    """Verify the .connection property provides access to the underlying DhanConnection."""

    def test_should_expose_underlying_connection(self, mocked_gateway_connection):
        """gateway.connection must return the DhanConnection instance."""
        gateway, mock_conn = mocked_gateway_connection
        assert gateway.connection is mock_conn

    def test_should_allow_direct_adapter_access_via_connection(self, mocked_gateway_connection):
        """Direct adapter access through gateway.connection must work."""
        gateway, mock_conn = mocked_gateway_connection
        mock_conn.market_data.get_ltp.return_value = Decimal("2500.50")
        ltp = gateway.connection.market_data.get_ltp("RELIANCE", "NSE")
        assert ltp == Decimal("2500.50")
