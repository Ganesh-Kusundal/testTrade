"""Orders adapter — place, modify, cancel, orderbook, tradebook.

Provides an OrdersAdapter for the Dhan broker integration that bridges
SCALPR domain Order/Fill types with Dhan's REST API.

Key design principles:
- Idempotency cache prevents duplicate order submissions
- DhanMapper handles all domain↔DTO translations (pure functions)
- http_client handles retry, rate limiting, circuit breaker
- All returns are SCALPR domain types (Fill, Order, dict)
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.brokers.dhan.dtos import DhanOrderResponse
from scalpr.brokers.dhan.exceptions import OrderError
from scalpr.brokers.dhan.http_client import DhanHttpClient
from scalpr.brokers.dhan.mapper import DhanMapper
from scalpr.brokers.dhan.resolver import SymbolResolver
from scalpr.domain.fill import Fill
from scalpr.domain.order import Order, OrderState, OrderType

logger = logging.getLogger(__name__)


class OrdersAdapter:
    """Adapter for order operations against Dhan API.

    Provides methods for:
    - Placing orders with idempotency protection
    - Modifying existing orders
    - Cancelling active orders
    - Fetching orderbook (all orders for the day)
    - Fetching tradebook (all fills for the day)

    Thread-safety: Idempotency cache is protected by a threading.Lock.
    The lock covers the check-and-add operations but NOT the API call itself,
    so concurrent orders with different correlation_ids proceed in parallel.
    """

    def __init__(self, client: DhanHttpClient, resolver: SymbolResolver):
        """Initialise OrdersAdapter.

        Args:
            client: Configured DhanHttpClient with auth, retry, circuit breaker.
            resolver: SymbolResolver for symbol→security_id lookups.
        """
        self._client = client
        self._resolver = resolver
        self._idempotency_cache: set[str] = set()
        self._in_flight: set[str] = set()  # correlation_ids currently being submitted
        self._cache_lock = threading.Lock()

    def place_order(self, order: Order) -> Fill:
        """Place a new order and return the resulting Fill.

        Idempotency: If the order's correlation_id has already been submitted,
        raises OrderError to prevent duplicate orders.

        Args:
            order: SCALPR Order domain object.

        Returns:
            Fill representing the execution result.

        Raises:
            OrderError: If idempotency check fails, mapping fails, or API rejects.
        """
        # ── Idempotency check (lock-protected) ─────────────────────────
        correlation_id = order.correlation_id or order.order_id
        with self._cache_lock:
            if correlation_id in self._idempotency_cache or correlation_id in self._in_flight:
                raise OrderError(
                    f"Duplicate order blocked: correlation_id={correlation_id!r} "
                    f"already submitted"
                )
            self._in_flight.add(correlation_id)

        # ── Pre-flight validation, resolution, mapping, and API call ───
        # All wrapped in try/except to guarantee _in_flight cleanup on failure.
        try:
            self._validate_order(order)

            # ── Resolve security_id ────────────────────────────────────
            try:
                inst = self._resolver.resolve(order.symbol, order.exchange.value)
                security_id = inst.security_id
            except Exception as exc:
                raise OrderError(
                    f"Cannot resolve security_id for {order.symbol} on {order.exchange}: {exc}"
                ) from exc

            # ── Map domain → Dhan DTO ─────────────────────────────────
            dhan_req_result = DhanMapper.order_to_dhan_request(order, self._client.client_id, security_id)
            if not dhan_req_result.is_ok:
                raise OrderError(f"Order mapping failed: {dhan_req_result.error}")

            dhan_req = dhan_req_result.value

            # Build JSON payload from DTO
            payload: dict[str, Any] = {
                "dhanClientId": dhan_req.dhanClientId,
                "correlationId": dhan_req.correlationId,
                "transactionType": dhan_req.transactionType,
                "exchangeSegment": dhan_req.exchangeSegment,
                "productType": dhan_req.productType,
                "orderType": dhan_req.orderType,
                "quantity": dhan_req.quantity,
                "price": str(dhan_req.price) if dhan_req.price else "0",  # Fixed: use str to preserve Decimal precision
                "triggerPrice": str(dhan_req.triggerPrice) if dhan_req.triggerPrice else "0",  # Fixed: use str
                "securityId": dhan_req.securityId,
                "validity": dhan_req.validity,
            }

            logger.info(
                "placing_order",
                extra={
                    "order_id": order.order_id,
                    "correlation_id": correlation_id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "quantity": order.quantity,
                    "price": float(order.price),
                },
            )

            # ── Call API ───────────────────────────────────────────────
            response_data = self._client.post("/orders", json=payload)
        except OrderError:
            # Remove from in-flight on failure so retry is possible; re-raise as-is
            with self._cache_lock:
                self._in_flight.discard(correlation_id)
            raise
        except Exception as exc:
            # Remove from in-flight on failure so retry is possible
            with self._cache_lock:
                self._in_flight.discard(correlation_id)
            # Do NOT add to idempotency cache on failure — allow retry
            raise OrderError(f"Order placement failed: {exc}") from exc

        # ── Mark idempotency (lock-protected) ──────────────────────────
        with self._cache_lock:
            self._idempotency_cache.add(correlation_id)
            self._in_flight.discard(correlation_id)

        # ── Parse response ─────────────────────────────────────────────
        order_id = response_data.get("orderId", order.order_id)
        order_status = response_data.get("orderStatus", "")

        # Build DhanOrderResponse DTO for mapper
        dhan_response = DhanOrderResponse(
            orderId=order_id,
            orderStatus=order_status,
            errorCode=response_data.get("errorCode", ""),
            errorMessage=response_data.get("errorMessage", ""),
        )

        # Check for rejection in response
        if dhan_response.orderStatus == "REJECTED":
            raise OrderError(
                f"Order rejected by broker: {dhan_response.errorMessage} "
                f"(order_id={order_id})"
            )

        # ── Extract fill details ───────────────────────────────────────
        # Dhan returns filled quantity and price in the response
        traded_quantity = int(response_data.get("tradedQuantity", 0))
        traded_price = Decimal(str(response_data.get("tradedPrice", 0)))

        # For MARKET orders, traded_price might be 0 if not filled yet
        # Dhan converts MARKET orders to LIMIT with MPP (Market Protection Price)
        # Don't fallback to order.price (which is 0 for MARKET orders)
        if order.order_type == OrderType.MARKET:
            fill_qty = traded_quantity if traded_quantity > 0 else 0
            fill_price = traded_price if traded_price > 0 else Decimal("0")
            if fill_price == 0:
                logger.warning(
                    "market_order_no_fill_price",
                    extra={
                        "order_id": order_id,
                        "status": order_status,
                        "note": "MARKET_ORDER_NOT_FILLED_YET_MPP_CONVERSION",
                    },
                )
        else:
            # LIMIT orders: use order price as fallback
            fill_qty = traded_quantity if traded_quantity > 0 else order.quantity
            fill_price = traded_price if traded_price > 0 else order.price

        fill_result = DhanMapper.dhan_response_to_fill(
            dhan_response, order, fill_price=fill_price, fill_qty=fill_qty
        )
        if not fill_result.is_ok:
            raise OrderError(f"Fill mapping failed: {fill_result.error}")

        fill = fill_result.value
        logger.info(
            "order_placed",
            extra={
                "order_id": order_id,
                "fill_id": fill.fill_id,
                "fill_qty": fill.quantity,
                "fill_price": float(fill.price),
            },
        )
        return fill

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
            OrderError: If modification fails.
        """
        if quantity <= 0:
            raise OrderError(f"Invalid quantity for modify: {quantity}")

        payload: dict[str, Any] = {
            "orderId": order_id,
            "price": str(price) if price else "0",  # Fixed: use str to preserve Decimal precision
            "quantity": quantity,
        }
        if trigger_price is not None:
            payload["triggerPrice"] = str(trigger_price)  # Fixed: use str

        logger.info(
            "modifying_order",
            extra={
                "order_id": order_id,
                "price": float(price),
                "quantity": quantity,
                "trigger_price": float(trigger_price) if trigger_price else None,
            },
        )

        try:
            response_data = self._client.put(f"/orders/{order_id}", json=payload)
        except Exception as exc:
            raise OrderError(f"Order modification failed: {exc}") from exc

        # Check response status
        status = response_data.get("orderStatus", "")
        if status == "REJECTED":
            error_msg = response_data.get("errorMessage", "unknown error")
            raise OrderError(f"Modify rejected: {error_msg} (order_id={order_id})")

        logger.info("order_modified", extra={"order_id": order_id, "status": status})
        return True

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order.

        Args:
            order_id: Dhan order ID to cancel.

        Returns:
            True if cancellation was successful.

        Raises:
            OrderError: If cancellation fails.
        """
        logger.info("cancelling_order", extra={"order_id": order_id})

        try:
            response_data = self._client.delete(f"/orders/{order_id}")
        except Exception as exc:
            raise OrderError(f"Order cancellation failed: {exc}") from exc

        status = response_data.get("orderStatus", "")
        if status == "REJECTED":
            error_msg = response_data.get("errorMessage", "unknown error")
            raise OrderError(f"Cancel rejected: {error_msg} (order_id={order_id})")

        logger.info("order_cancelled", extra={"order_id": order_id, "status": status})
        return True

    def get_orderbook(self) -> list[dict[str, Any]]:
        """Fetch the day's orderbook from Dhan.

        Returns:
            List of order dicts with fields:
            - orderId, symbol, exchangeSegment, side, orderType,
              quantity, price, triggerPrice, status, filledQuantity,
              tradedPrice, createdTime, updatedTime

        Raises:
            OrderError: If fetching orderbook fails.
        """
        logger.debug("fetching_orderbook")

        try:
            response_data = self._client.get("/orders")
        except Exception as exc:
            raise OrderError(f"Orderbook fetch failed: {exc}") from exc

        raw_orders = response_data if isinstance(response_data, list) else response_data.get("data", [])

        orderbook = []
        for raw in raw_orders:
            order = {
                "order_id": raw.get("orderId", ""),
                "symbol": raw.get("tradingSymbol", raw.get("securityId", "")),
                "exchange_segment": raw.get("exchangeSegment", ""),
                "side": raw.get("transactionType", ""),
                "order_type": raw.get("orderType", ""),
                "quantity": int(raw.get("quantity", 0)),
                "price": Decimal(str(raw.get("price", 0))),
                "trigger_price": Decimal(str(raw.get("triggerPrice", 0))),
                "status": raw.get("orderStatus", ""),
                "filled_quantity": int(raw.get("tradedQuantity", 0)),
                "traded_price": Decimal(str(raw.get("tradedPrice", 0))),
                "product_type": raw.get("productType", ""),
                "validity": raw.get("validity", ""),
                "created_time": raw.get("createTime", ""),
                "updated_time": raw.get("updateTime", ""),
                "correlation_id": raw.get("correlationId", ""),
                "reject_reason": raw.get("remarks", ""),
            }
            orderbook.append(order)

        logger.debug(f"orderbook_fetched: {len(orderbook)} orders")
        return orderbook

    def get_tradebook(self) -> list[dict[str, Any]]:
        """Fetch the day's tradebook (execution fills) from Dhan.

        Returns:
            List of trade dicts with fields:
            - tradeId, orderId, symbol, side, quantity, price,
              tradeDate, exchangeSegment, productType

        Raises:
            OrderError: If fetching tradebook fails.
        """
        logger.debug("fetching_tradebook")

        try:
            response_data = self._client.get("/trades")
        except Exception as exc:
            raise OrderError(f"Tradebook fetch failed: {exc}") from exc

        raw_trades = response_data if isinstance(response_data, list) else response_data.get("data", [])

        tradebook = []
        for raw in raw_trades:
            trade = {
                "trade_id": raw.get("tradeId", ""),
                "order_id": raw.get("orderId", ""),
                "symbol": raw.get("tradingSymbol", raw.get("securityId", "")),
                "side": raw.get("transactionType", ""),
                "quantity": int(raw.get("quantity", 0)),
                "price": Decimal(str(raw.get("price", 0))),
                "trade_date": raw.get("tradeDate", ""),
                "exchange_segment": raw.get("exchangeSegment", ""),
                "product_type": raw.get("productType", ""),
            }
            tradebook.append(trade)

        logger.debug(f"tradebook_fetched: {len(tradebook)} trades")
        return tradebook

    def clear_idempotency_cache(self) -> None:
        """Clear the idempotency cache.

        Should be called at session start or end-of-day to prevent
        stale correlation_ids from blocking new orders.
        """
        with self._cache_lock:
            count = len(self._idempotency_cache)
            self._idempotency_cache.clear()
        logger.info(f"idempotency_cache_cleared: {count} entries removed")

    @staticmethod
    def _validate_order(order: Order) -> None:
        """Validate order before submission.

        Raises:
            OrderError: If order is invalid.
        """
        if order.quantity <= 0:
            raise OrderError(f"Invalid quantity: {order.quantity}")

        if order.order_type == OrderType.LIMIT and order.price <= 0:
            raise OrderError(f"LIMIT order must have price > 0: {order.price}")

        if not order.symbol:
            raise OrderError("Order symbol cannot be empty")

        if order.state.is_terminal:
            raise OrderError(
                f"Cannot place order in terminal state: {order.state.value}"
            )
