from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Generic, TypeVar

from scalpr.brokers.dhan.dtos import DhanOrderRequest, DhanOrderResponse
from scalpr.brokers.dhan.resolution import SEGMENT_TO_EXCHANGE, exchange_to_wire
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.domain.values import ZERO

T = TypeVar('T')
E = TypeVar('E')


class Result(Generic[T, E]):
    """Monadic Result wrapper for pure, error-safe computations."""
    def __init__(self, is_ok: bool, value: T | None = None, error: E | None = None):
        self.is_ok = is_ok
        self._value = value
        self._error = error

    @property
    def value(self) -> T:
        if not self.is_ok:
            raise ValueError(f"Cannot access value of failure Result: {self._error}")
        assert self._value is not None
        return self._value

    @property
    def error(self) -> E:
        if self.is_ok:
            raise ValueError("Cannot access error of success Result")
        assert self._error is not None
        return self._error

    @classmethod
    def success(cls, value: T) -> Result[T, E]:
        return cls(True, value=value)

    @classmethod
    def failure(cls, error: E) -> Result[T, E]:
        return cls(False, error=error)


# Dhan API expects "SL" and "SL-M", not the enum values "STOP_LOSS" / "STOP_LOSS_MARKET"
_ORDER_TYPE_TO_DHAN: dict[OrderType, str] = {
    OrderType.LIMIT: "LIMIT",
    OrderType.MARKET: "MARKET",
    OrderType.STOP_LOSS: "SL",
    OrderType.STOP_LOSS_MARKET: "SL-M",
}


class DhanMapper:
    """Pure data transformer between Domain objects and Dhan API DTOs."""

    @staticmethod
    def order_to_dhan_request(
        order: Order,
        client_id: str,
        security_id: str,
        exchange_segment: str | None = None,
    ) -> Result[DhanOrderRequest, str]:
        try:
            # Prefer the resolver-derived wire segment (segment-aware, e.g.
            # BSE_FNO for SENSEX options). Fall back to the exchange-only
            # mapping for callers that cannot supply one.
            if exchange_segment:
                segment = exchange_segment
            else:
                try:
                    segment = exchange_to_wire(order.exchange)
                except ValueError:
                    return Result.failure(f"Unsupported exchange: {order.exchange}")

            return Result.success(
                DhanOrderRequest(
                    dhanClientId=client_id,
                    correlationId=order.correlation_id or "",
                    transactionType=order.side.value,
                    exchangeSegment=segment,
                    productType=order.product_type,
                    orderType=_ORDER_TYPE_TO_DHAN[order.order_type],
                    quantity=order.quantity,
                    price=order.price,
                    triggerPrice=order.trigger_price,
                    securityId=security_id,
                )
            )
        except Exception as exc:
            return Result.failure(str(exc))

    @staticmethod
    def dhan_response_to_fill(response: DhanOrderResponse, order: Order, fill_price: Decimal, fill_qty: int) -> Result[Fill, str]:
        try:
            if not isinstance(fill_price, Decimal):
                return Result.failure("price must be Decimal")

            return Result.success(
                Fill(
                    fill_id=f"f_{response.orderId}",
                    order_id=response.orderId,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=fill_qty,
                    price=fill_price,
                    timestamp=datetime.now(timezone.utc),
                )
            )
        except Exception as exc:
            return Result.failure(str(exc))

    @staticmethod
    def dhan_position_to_domain(pos: dict[str, Any]) -> Result[Position, str]:
        try:
            symbol = pos.get("symbol", "")
            exchange_str = pos.get("exchange", "NSE")
            try:
                exchange = Exchange(exchange_str)
            except ValueError:
                exchange = Exchange.NSE

            quantity = int(pos.get("quantity", 0))
            avg_price = Decimal(str(pos.get("avgPrice", "0")))
            ltp = Decimal(str(pos.get("ltp", "0")))
            realised_pnl = Decimal(str(pos.get("realizedPnl", "0")))

            # Determine side and state
            if quantity > 0:
                side = PositionSide.LONG
                state = PositionState.OPEN
            elif quantity < 0:
                side = PositionSide.SHORT
                state = PositionState.OPEN
            else:
                side = PositionSide.FLAT
                state = PositionState.FLAT

            # Calculate unrealised PnL
            if quantity > 0:
                unrealised = Decimal(quantity) * (ltp - avg_price)
            elif quantity < 0:
                unrealised = Decimal(abs(quantity)) * (avg_price - ltp)
            else:
                unrealised = ZERO

            return Result.success(
                Position(
                    symbol=symbol,
                    exchange=exchange,
                    quantity=quantity,
                    avg_price=avg_price,
                    ltp=ltp,
                    unrealised_pnl=unrealised,
                    realised_pnl=realised_pnl,
                    position_side=side,
                    state=state,
                )
            )
        except Exception as exc:
            return Result.failure(str(exc))

    @staticmethod
    def raw_order_to_order(raw: dict[str, Any]) -> Result[Order, str]:
        """Map a raw orderbook entry to a SCALPR Order domain object.

        Args:
            raw: Dict from OrdersAdapter.get_orderbook().

        Returns:
            Result wrapping an Order domain object, or an error message.
        """
        try:
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

            side_str = raw.get("side", "").upper()
            side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL

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

            exchange_segment = raw.get("exchange_segment", "NSE_EQ")
            exchange_segment_upper = exchange_segment.upper()
            exchange = Exchange.NSE
            if "MCX" in exchange_segment_upper:
                exchange = Exchange.MCX
            elif "BSE" in exchange_segment_upper:
                exchange = Exchange.BSE

            return Result.success(
                Order(
                    order_id=raw.get("order_id", ""),
                    symbol=raw.get("symbol", ""),
                    exchange=exchange,
                    side=side,
                    order_type=order_type,
                    quantity=raw.get("quantity", 0),
                    price=raw.get("price", ZERO),
                    trigger_price=raw.get("trigger_price", ZERO),
                    state=state,
                    filled_quantity=raw.get("filled_quantity", 0),
                    avg_price=raw.get("traded_price", ZERO),
                    product_type=raw.get("product_type", "INTRADAY"),
                    validity=raw.get("validity", "DAY"),
                    reject_reason=raw.get("reject_reason", ""),
                    correlation_id=raw.get("correlation_id"),
                )
            )
        except Exception as exc:
            return Result.failure(str(exc))

    @staticmethod
    def raw_trade_to_fill(raw: dict[str, Any]) -> Result[Fill, str]:
        """Map a raw tradebook entry to a SCALPR Fill domain object.

        Args:
            raw: Dict from OrdersAdapter.get_tradebook().

        Returns:
            Result wrapping a Fill domain object, or an error message.
        """
        try:
            side_str = raw.get("side", "").upper()
            side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL

            trade_date_str = raw.get("trade_date", "")
            timestamp = None
            if trade_date_str:
                with contextlib.suppress(ValueError, TypeError):
                    timestamp = datetime.fromisoformat(trade_date_str)

            return Result.success(
                Fill(
                    fill_id=raw.get("trade_id", ""),
                    order_id=raw.get("order_id", ""),
                    symbol=raw.get("symbol", ""),
                    side=side,
                    quantity=raw.get("quantity", 0),
                    price=raw.get("price", ZERO),
                    timestamp=timestamp,
                    exchange=SEGMENT_TO_EXCHANGE.get(raw.get("exchange_segment", ""), ""),
                )
            )
        except Exception as exc:
            return Result.failure(str(exc))
