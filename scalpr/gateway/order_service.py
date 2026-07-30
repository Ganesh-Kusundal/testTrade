from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.instrument import Exchange, ResolvedInstrument
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType, OrderRequest, ModifyOrderRequest, ProductType, Validity
from scalpr.engine.clock import Clock
from scalpr.engine.execution_engine import CancelOrder, ModifyOrder, SubmitOrder
from scalpr.engine.message_bus import MessageBus

logger = logging.getLogger(__name__)


class OrderService:
    """Broker-agnostic order service.

    Validates, constructs, and routes order commands through the message bus.
    The broker adapter (DhanClient) subscribes to the broker-specific topics
    and publishes back fill/accept/reject events.
    """

    def __init__(
        self,
        client: DhanClient,
        bus: MessageBus,
        clock: Clock,
        risk: Any = None,
    ) -> None:
        self._client = client
        self._bus = bus
        self._clock = clock
        self._risk = risk

    def place(self, request: OrderRequest) -> Order:
        """Place a new order.

        Validates via RiskService (if configured), constructs an Order domain
        object, and publishes SubmitOrder on the bus for the broker to process.
        """
        if self._risk is not None:
            self._risk.validate(request)

        resolved = self._resolve_instrument(request)
        symbol = resolved.trading_symbol

        order = Order(
            order_id=request.correlation_id or f"ord-{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            exchange=resolved.exchange,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price or Decimal("0"),
            trigger_price=request.trigger_price or Decimal("0"),
            product_type=request.product.value,
            validity=request.validity.value,
            correlation_id=request.correlation_id,
        )

        self._bus.publish(
            "exec.command.submit",
            SubmitOrder(order=order, broker=self._client.broker),
        )
        return order

    def place_slice(self, request: OrderRequest) -> list[Order]:
        """Place an order in slices based on freeze quantity."""
        resolved = self._resolve_instrument(request)
        freeze_qty = resolved.freeze_quantity or request.quantity
        slice_size = min(freeze_qty, request.quantity)

        orders: list[Order] = []
        remaining = request.quantity
        while remaining > 0:
            slice_qty = min(slice_size, remaining)
            slice_req = OrderRequest(
                instrument=request.instrument,
                side=request.side,
                quantity=slice_qty,
                order_type=request.order_type,
                product=request.product,
                validity=request.validity,
                price=request.price,
                trigger_price=request.trigger_price,
                correlation_id=request.correlation_id,
            )
            orders.append(self.place(slice_req))
            remaining -= slice_qty
        return orders

    def modify(self, order_id: str, request: ModifyOrderRequest) -> Order:
        """Modify an existing order."""
        updates: dict[str, Any] = {}
        if request.quantity is not None:
            updates["quantity"] = request.quantity
        if request.price is not None:
            updates["price"] = request.price
        if request.trigger_price is not None:
            updates["trigger_price"] = request.trigger_price
        if request.validity is not None:
            updates["validity"] = request.validity.value

        self._bus.publish(
            "exec.command.modify",
            ModifyOrder(order_id=order_id, updates=updates, broker=self._client.broker),
        )
        # Return a modified Order (state will be updated by engine when
        # the broker confirms the modification)
        return Order(
            order_id=order_id,
            symbol=order_id,
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=updates.get("quantity", 1),
            price=Decimal("0"),
            state=OrderState.OPEN,
        )

    def cancel(self, order_id: str) -> Order:
        """Cancel an existing order."""
        self._bus.publish(
            "exec.command.cancel",
            CancelOrder(order_id=order_id, broker=self._client.broker),
        )
        # Return a placeholder Order — the engine will update state when
        # the broker confirms cancellation
        return Order(
            order_id=order_id,
            symbol=order_id,
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1,
            price=Decimal("0"),
            state=OrderState.CANCELLED,
        )

    def get(self, order_id: str) -> Order | None:
        """Fetch order detail from the broker."""
        detail = self._client.get_order_detail(order_id)
        return self._map_order_detail(detail)

    def list(self) -> list[Order]:
        """Fetch all orders from the broker."""
        # DhanClient doesn't have a direct order book method; use order_report
        # for individual orders. For now, return empty list.
        return []

    def trades(self) -> list[Any]:
        """Fetch all trades from the broker."""
        return self._client.get_trade_book()

    def trades_for_order(self, order_id: str) -> list[Any]:
        """Fetch trades for a specific order."""
        all_trades = self._client.get_trade_book()
        return [t for t in all_trades if t.get("orderId") == order_id]

    def _resolve_instrument(self, request: OrderRequest) -> ResolvedInstrument:
        """Resolve the instrument from the request."""
        if hasattr(request.instrument, "resolved"):
            return request.instrument.resolved
        return self._client.resolve_instrument(request.instrument)

    def _map_order_detail(self, detail: dict[str, Any]) -> Order | None:
        """Map a raw Dhan order detail dict to a domain Order."""
        if not detail:
            return None
        return Order(
            order_id=detail.get("orderId", ""),
            symbol=detail.get("tradingSymbol", detail.get("symbol", "")),
            exchange=self._client._resolver.resolve_full(detail.get("tradingSymbol", ""), "NSE").exchange,
            side=OrderSide(detail.get("transactionType", "BUY")),
            order_type=OrderType(detail.get("orderType", "LIMIT")),
            quantity=int(detail.get("quantity", 0)),
            price=Decimal(str(detail.get("price", 0))),
            state=OrderState(detail.get("status", "PENDING")),
            product_type=detail.get("productType", "INTRADAY"),
            validity=detail.get("validity", "DAY"),
            trigger_price=Decimal(str(detail.get("triggerPrice", 0))),
            filled_quantity=int(detail.get("filledQty", 0)),
            avg_price=Decimal(str(detail.get("avgPrice", 0))),
        )
