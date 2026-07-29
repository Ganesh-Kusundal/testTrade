from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any

from scalpr.domain.fill import Fill
from scalpr.domain.order import Order
from scalpr.domain.position import Position


class ITradingPort(ABC):
    """Order lifecycle operations — submit, modify, cancel, query orders/trades."""

    @abstractmethod
    def place_order(self, order: Order) -> Fill:
        """Place an order and return the resulting execution Fill."""
        pass

    @abstractmethod
    def modify_order(self, order_id: str, price: Decimal, quantity: int) -> bool:
        """Modify an existing order's price and quantity."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Order:
        """Fetch the current status of an order."""
        pass

    @abstractmethod
    def get_orders(self) -> list[Order]:
        """Fetch the full orderbook."""
        pass

    @abstractmethod
    def get_tradebook(self) -> list[Fill]:
        """Fetch the day's tradebook (execution fills)."""
        pass

    @abstractmethod
    def square_off_all(self) -> list[Fill]:
        """Square off all current positions and return execution Fills."""
        pass


class IMarketDataPort(ABC):
    """Market data operations — quotes, LTP, historical data."""

    @abstractmethod
    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Decimal:
        """Get Last Traded Price for a symbol."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str, exchange: str = "NSE") -> dict[str, Any]:
        """Get full market quote for a symbol."""
        pass

    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch historical OHLCV candlestick data."""
        pass


class IAccountPort(ABC):
    """Account operations — positions, holdings, margins, fund limits."""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Fetch current open positions."""
        pass

    @abstractmethod
    def get_holdings(self) -> list[Position]:
        """Fetch long-term delivery holdings."""
        pass

    @abstractmethod
    def get_margins(self) -> dict[str, Any]:
        """Fetch available margin limits."""
        pass

    @abstractmethod
    def get_fund_limits(self) -> dict[str, Any]:
        """Fetch available margin limits and fund details."""
        pass


class IBrokerGateway(ITradingPort, IMarketDataPort, IAccountPort, ABC):
    """Combined interface for backward compatibility.

    Inherits all three focused port interfaces (ITradingPort, IMarketDataPort,
    IAccountPort) and adds gateway lifecycle methods. New code should type
    against the focused sub-interfaces; existing consumers continue to work
    with IBrokerGateway.
    """

    @abstractmethod
    def is_connected(self) -> bool:
        """Check connection state with broker."""
        pass

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to broker API."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection and release resources."""
        pass

    @property
    @abstractmethod
    def connection(self) -> Any | None:
        """Return the underlying broker connection object.

        Provides typed access to the connection without going through
        the adapters() dict. Returns None if not connected.
        """
        ...

    def adapters(self) -> dict[str, Any]:
        """Return broker-specific adapters for advanced operations.

        Returns a dict of adapter objects that the broker-agnostic layer
        can use for operations like option chains. Brokers that don't
        provide adapters should return an empty dict.

        This method eliminates the need for the broker-agnostic layer to
        reach into broker-specific private state (Law of Demeter violation).
        """
        return {}
