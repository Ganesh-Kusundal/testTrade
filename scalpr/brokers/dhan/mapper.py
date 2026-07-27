from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Generic, TypeVar

from scalpr.brokers.dhan.dtos import DhanOrderRequest, DhanOrderResponse
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order
from scalpr.domain.position import Position, PositionSide, PositionState

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


class DhanMapper:
    """Pure data transformer between Domain objects and Dhan API DTOs."""

    @staticmethod
    def order_to_dhan_request(order: Order, client_id: str, security_id: str) -> Result[DhanOrderRequest, str]:
        try:
            # Exchange segment mapping
            if order.exchange == Exchange.NSE:
                segment = "NSE_EQ"
            elif order.exchange == Exchange.MCX:
                segment = "MCX_COMM"  # Fixed: was "MCXCOMM" (missing underscore)
            else:
                return Result.failure(f"Unsupported exchange: {order.exchange}")

            return Result.success(
                DhanOrderRequest(
                    dhanClientId=client_id,
                    correlationId=order.correlation_id or "",
                    transactionType=order.side.value,
                    exchangeSegment=segment,
                    productType=order.product_type,
                    orderType=order.order_type.value,
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
                unrealised = Decimal("0")

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
