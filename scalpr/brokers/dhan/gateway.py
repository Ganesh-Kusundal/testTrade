"""Dhan broker gateway — thin facade over DhanConnection implementing IBrokerGateway.

This module replaces the previous simulated gateway with a production-ready
implementation that delegates all operations to the Wave 3 adapter stack
(MarketDataAdapter, OrdersAdapter, PortfolioAdapter, HistoricalDataAdapter).

Design principle: the gateway is a thin facade. All business logic lives in
the adapters. The gateway exists only to satisfy the IBrokerGateway contract
and provide a clean entry point for SCALPR's execution engine.

As Dr. Venkat says: "A system that is fast and wrong is more dangerous than
a system that is slow and right." — delegation over duplication.
"""

from __future__ import annotations

import contextlib
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.brokers.dhan.connection import DhanConnection
from scalpr.brokers.dhan.exceptions import BrokerError
from scalpr.brokers.dhan.exceptions import RateLimitError as DhanRateLimitError
from scalpr.brokers.dhan.segments import SEGMENT_TO_EXCHANGE
from scalpr.brokers.errors import RateLimitError
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position

logger = logging.getLogger(__name__)


class DhanGateway(IBrokerGateway):
    """Production Dhan broker gateway implementing IBrokerGateway.

    Thin facade over DhanConnection. All logic is delegated to the
    adapter stack. No business logic, no simulated responses.

    Usage::

        gateway = DhanGateway({
            "client_id": "...",
            "access_token": "...",
        })
        gateway.connect()
        ltp = gateway.get_ltp("RELIANCE", "NSE")
        fill = gateway.place_order(order)
        positions = gateway.get_positions()
        gateway.disconnect()
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialise DhanGateway with configuration.

        Args:
            config: Configuration dict passed through to DhanConnection.
                Required keys:
                - client_id (str): Dhan client ID
                - access_token (str): Dhan access token
                Optional keys passed to DhanConnection:
                - base_url, timeout, token_refresh_fn, enable_retry,
                  instruments_force_refresh
        """
        self._connection = DhanConnection(config)

    # ------------------------------------------------------------------
    # IBrokerGateway lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Establish connection to Dhan API.

        Delegates to DhanConnection.connect() which initialises the HTTP
        client, loads instruments, and verifies the connection.
        """
        self._connection.connect()

    def disconnect(self) -> None:
        """Close connection and release resources.

        Delegates to DhanConnection.disconnect().
        """
        self._connection.disconnect()

    def is_connected(self) -> bool:
        """Check if the gateway is connected to Dhan API.

        Returns:
            True if connected, False otherwise.
        """
        return self._connection.is_connected()

    # ------------------------------------------------------------------
    # IBrokerGateway — Market data
    # ------------------------------------------------------------------

    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Decimal:
        """Get Last Traded Price for a symbol.

        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            exchange: Exchange code (e.g., "NSE", "MCX")

        Returns:
            LTP as Decimal.

        Raises:
            BrokerError: If not connected or API call fails.
        """
        return self._connection.market_data.get_ltp(symbol, exchange)

    def get_quote(self, symbol: str, exchange: str = "NSE") -> dict[str, Any]:
        """Get full market quote for a symbol.

        Args:
            symbol: Trading symbol
            exchange: Exchange code

        Returns:
            Quote dict with ltp, open, high, low, close, volume, change.

        Raises:
            BrokerError: If not connected or API call fails.
        """
        return self._connection.market_data.get_quote(symbol, exchange)

    # ------------------------------------------------------------------
    # IBrokerGateway — Order operations
    # ------------------------------------------------------------------

    def place_order(self, order: Order) -> Fill:
        """Place a new order and return the resulting Fill.

        Delegates to OrdersAdapter.place_order() which handles:
        - Idempotency protection
        - Symbol resolution
        - Domain → Dhan DTO mapping
        - API call with retry/circuit breaker
        - Response → Fill mapping

        Args:
            order: SCALPR Order domain object.

        Returns:
            Fill representing the execution result.

        Raises:
            BrokerError: If order placement fails.
        """
        try:
            return self._connection.orders.place_order(order)
        except DhanRateLimitError as exc:
            raise RateLimitError(str(exc)) from exc

    def modify_order(self, order_id: str, price: Decimal, quantity: int, trigger_price: Decimal | None = None) -> bool:
        """Modify an existing order's price, quantity, and/or trigger price.

        Args:
            order_id: Dhan order ID to modify.
            price: New price (use 0 for market orders).
            quantity: New quantity.
            trigger_price: New trigger price for SL orders (optional).

        Returns:
            True if modification was successful.

        Raises:
            BrokerError: If modification fails.
        """
        return self._connection.orders.modify_order(order_id, price, quantity, trigger_price)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order.

        Args:
            order_id: Dhan order ID to cancel.

        Returns:
            True if cancellation was successful.

        Raises:
            BrokerError: If cancellation fails.
        """
        return self._connection.orders.cancel_order(order_id)

    def get_order_status(self, order_id: str) -> Order:
        """Fetch the current status of an order from the orderbook.

        Retrieves the orderbook and finds the matching order by ID.
        Maps the raw order data to a SCALPR Order domain object.

        Args:
            order_id: Dhan order ID to look up.

        Returns:
            Order domain object with current status.

        Raises:
            BrokerError: If orderbook fetch fails or order not found.
        """
        orderbook = self._connection.orders.get_orderbook()

        for entry in orderbook:
            if entry.get("order_id") == order_id:
                return self._map_raw_order_to_order(entry)

        raise BrokerError(f"Order not found in orderbook: order_id={order_id}")

    def get_orders(self) -> list[Order]:
        """Fetch the full orderbook from Dhan.

        Returns:
            List of Order domain objects for all orders today.

        Raises:
            BrokerError: If orderbook fetch fails.
        """
        raw_orders = self._connection.orders.get_orderbook()
        return [self._map_raw_order_to_order(raw) for raw in raw_orders]

    def get_tradebook(self) -> list[Fill]:
        """Fetch the day's tradebook (execution fills) from Dhan.

        Returns:
            List of Fill domain objects for all executions today.

        Raises:
            BrokerError: If tradebook fetch fails.
        """
        raw_trades = self._connection.orders.get_tradebook()
        return [self._map_raw_trade_to_fill(raw) for raw in raw_trades]

    # ------------------------------------------------------------------
    # IBrokerGateway — Portfolio
    # ------------------------------------------------------------------

    def get_positions(self) -> list[Position]:
        """Fetch current open positions.

        Delegates to PortfolioAdapter.get_positions() which returns
        only non-flat positions as SCALPR Position domain objects.

        Returns:
            List of Position domain objects.
        """
        return self._connection.portfolio.get_positions()

    def get_holdings(self) -> list[Position]:
        """Fetch long-term delivery holdings.

        Returns:
            List of Position domain objects for holdings.
        """
        return self._connection.portfolio.get_holdings()

    def get_margins(self) -> dict:
        """Fetch available margin limits and fund details.

        Delegates to PortfolioAdapter.get_fund_limits().

        Returns:
            Dict with keys:
            - available_margin (Decimal)
            - used_margin (Decimal)
            - total_balance (Decimal)
            - collateral (Decimal)
            - realtime (bool)
        """
        return self._connection.portfolio.get_fund_limits()

    def get_fund_limits(self) -> dict:
        """Fetch available margin limits and fund details.

        Alias for get_margins() — provided for clarity.

        Returns:
            Dict with margin and fund details.
        """
        return self.get_margins()

    # ------------------------------------------------------------------
    # IBrokerGateway — Historical data
    # ------------------------------------------------------------------

    def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch historical OHLCV candlestick data.

        Delegates to HistoricalDataAdapter.get_ohlcv().

        Args:
            symbol: Trading symbol
            exchange: Exchange code
            timeframe: Candle interval (e.g., "1m", "5m", "1H", "1D")
            from_date: Start date (inclusive)
            to_date: End date (inclusive)

        Returns:
            List of candle dicts with keys:
            timestamp, open, high, low, close, volume

        Raises:
            BrokerError: If not connected or API call fails.
        """
        return self._connection.historical.get_ohlcv(
            symbol, exchange, timeframe, from_date, to_date
        )

    # ------------------------------------------------------------------
    # IBrokerGateway — Square off
    # ------------------------------------------------------------------

    def square_off_all(self) -> list[Fill]:
        """Square off all current open positions with market orders.

        For each open position, places a counter market order:
        - LONG position → SELL market order
        - SHORT position → BUY market order

        Returns:
            List of Fill objects for each square-off execution.

        Raises:
            BrokerError: If any square-off order fails.
        """
        positions = self.get_positions()
        fills: list[Fill] = []

        for pos in positions:
            if pos.quantity == 0:
                continue

            side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY
            qty = abs(pos.quantity)

            order = Order(
                order_id=f"sq_{pos.symbol}_{id(pos)}",
                symbol=pos.symbol,
                exchange=pos.exchange,
                side=side,
                order_type=OrderType.MARKET,
                quantity=qty,
                price=pos.ltp if pos.ltp > 0 else Decimal("0"),
                state=OrderState.PENDING,
            )

            try:
                fill = self.place_order(order)
                fills.append(fill)
                logger.info(
                    "square_off_executed",
                    extra={
                        "symbol": pos.symbol,
                        "side": side.value,
                        "quantity": qty,
                        "fill_id": fill.fill_id,
                    },
                )
            except Exception as exc:
                logger.error(
                    "square_off_failed",
                    extra={
                        "symbol": pos.symbol,
                        "side": side.value,
                        "quantity": qty,
                        "error": str(exc),
                    },
                )
                raise BrokerError(
                    f"Square-off failed for {pos.symbol}: {exc}"
                ) from exc

        logger.info(f"square_off_all_complete: {len(fills)} positions closed")
        return fills

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_raw_order_to_order(raw: dict[str, Any]) -> Order:
        """Map a raw orderbook entry to a SCALPR Order domain object.

        Args:
            raw: Dict from OrdersAdapter.get_orderbook().

        Returns:
            Order domain object.
        """
        # Map order status string to OrderState
        status_str = raw.get("status", "").upper()
        state_map: dict[str, OrderState] = {
            "PENDING": OrderState.PENDING,
            "OPEN": OrderState.OPEN,
            "PARTIALLY FILLED": OrderState.PARTIALLY_FILLED,
            "FILLED": OrderState.FILLED,
            "CANCELLED": OrderState.CANCELLED,
            "REJECTED": OrderState.REJECTED,
            "EXPIRED": OrderState.EXPIRED,
            "TRIGGER PENDING": OrderState.PENDING,
        }
        state = state_map.get(status_str, OrderState.PENDING)

        # Map side string to OrderSide
        side_str = raw.get("side", "").upper()
        side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL

        # Map order type string to OrderType
        type_str = raw.get("order_type", "").upper()
        type_map: dict[str, OrderType] = {
            "LIMIT": OrderType.LIMIT,
            "MARKET": OrderType.MARKET,
            "SL": OrderType.STOP_LOSS,
            "SL-M": OrderType.STOP_LOSS_MARKET,
            "STOPLIMIT": OrderType.STOP_LOSS,
            "STOPMARKET": OrderType.STOP_LOSS_MARKET,
            "STOP LOSS": OrderType.STOP_LOSS,
            "STOP LOSS MARKET": OrderType.STOP_LOSS_MARKET,
        }
        order_type = type_map.get(type_str, OrderType.LIMIT)

        # Map exchange segment to Exchange
        exchange_segment = raw.get("exchange_segment", "NSE_EQ")
        exchange_segment_upper = exchange_segment.upper()
        exchange = Exchange.NSE  # Default
        if "MCX" in exchange_segment_upper:
            exchange = Exchange.MCX
        elif "BSE" in exchange_segment_upper:
            exchange = Exchange.BSE

        return Order(
            order_id=raw.get("order_id", ""),
            symbol=raw.get("symbol", ""),
            exchange=exchange,
            side=side,
            order_type=order_type,
            quantity=raw.get("quantity", 0),
            price=raw.get("price", Decimal("0")),
            trigger_price=raw.get("trigger_price", Decimal("0")),
            state=state,
            filled_quantity=raw.get("filled_quantity", 0),
            avg_price=raw.get("traded_price", Decimal("0")),
            product_type=raw.get("product_type", "INTRADAY"),
            validity=raw.get("validity", "DAY"),
            reject_reason=raw.get("reject_reason", ""),
            correlation_id=raw.get("correlation_id"),
        )

    @staticmethod
    def _map_raw_trade_to_fill(raw: dict[str, Any]) -> Fill:
        """Map a raw tradebook entry to a SCALPR Fill domain object.

        Args:
            raw: Dict from OrdersAdapter.get_tradebook().

        Returns:
            Fill domain object.
        """
        side_str = raw.get("side", "").upper()
        side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL

        trade_date_str = raw.get("trade_date", "")
        timestamp = None
        if trade_date_str:
            with contextlib.suppress(ValueError, TypeError):
                timestamp = datetime.fromisoformat(trade_date_str)

        return Fill(
            fill_id=raw.get("trade_id", ""),
            order_id=raw.get("order_id", ""),
            symbol=raw.get("symbol", ""),
            side=side,
            quantity=raw.get("quantity", 0),
            price=raw.get("price", Decimal("0")),
            timestamp=timestamp,
            exchange=SEGMENT_TO_EXCHANGE.get(raw.get("exchange_segment", ""), ""),
        )

    # ------------------------------------------------------------------
    # Properties for direct adapter access (when needed)
    # ------------------------------------------------------------------

    @property
    def connection(self) -> DhanConnection:
        """Access the underlying DhanConnection.

        Use this when you need direct access to adapters for operations
        not covered by IBrokerGateway (e.g., batch LTP, depth, tradebook).
        """
        return self._connection
