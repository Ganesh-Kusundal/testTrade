from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from scalpr.domain.contracts import BrokerClientProtocol
from scalpr.domain.instrument import Exchange, ResolvedInstrument
from scalpr.domain.order import (
    ModifyOrderRequest,
    Order,
    OrderRequest,
    OrderSide,
    OrderState,
    OrderType,
    broker_status_to_order_state,
)
from scalpr.engine.clock import Clock
from scalpr.engine.execution_engine import CancelOrder, ModifyOrder, SubmitOrder
from scalpr.engine.message_bus import MessageBus

logger = logging.getLogger(__name__)


def _safe_order_state(raw: str) -> OrderState:
    """Map a broker status string to an OrderState, defaulting to PENDING.

    Uses the canonical ``broker_status_to_order_state`` from the domain
    layer — the single source of truth for status translations.
    """
    return broker_status_to_order_state(raw)


class OrderService:
    """Broker-agnostic order service.

    Validates, constructs, and routes order commands through the message bus.
    The broker adapter (DhanClient) subscribes to the broker-specific topics
    and publishes back fill/accept/reject events.
    """

    def __init__(
        self,
        client: BrokerClientProtocol,
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

    def modify(self, order_id: str, request: ModifyOrderRequest) -> None:
        """Modify an existing order.

        Publishes a ModifyOrder command on the bus.  Returns None — the
        real state lives in the ExecutionEngine cache and will be updated
        when the broker confirms on exec.event.modified.<broker>.
        """
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

    def cancel(self, order_id: str) -> None:
        """Cancel an existing order.

        Publishes a CancelOrder command on the bus.  Returns None — the
        order stays in its current state in the engine cache until the
        broker confirms on exec.event.cancelled.<broker>.
        """
        self._bus.publish(
            "exec.command.cancel",
            CancelOrder(order_id=order_id, broker=self._client.broker),
        )

    def get(self, order_id: str) -> Order | None:
        """Fetch order detail from the broker."""
        detail = self._client.get_order_detail(order_id)
        return self._map_order_detail(detail)

    def list(self) -> list[Order]:
        """Fetch all orders from the broker."""
        # TODO: implement order book listing via the bus or adapter
        return []

    def trades(self) -> list[Any]:
        """Fetch all trades from the broker."""
        return self._client.get_trade_book()

    def trades_for_order(self, order_id: str) -> list[Any]:
        """Fetch trades for a specific order."""
        all_trades = self._client.get_trade_book()
        if isinstance(all_trades, list):
            return [t for t in all_trades if t.get("orderId") == order_id]
        return []

    def _resolve_instrument(self, request: OrderRequest) -> ResolvedInstrument:
        """Resolve the instrument from the request."""
        if hasattr(request.instrument, "resolved"):
            return request.instrument.resolved
        return self._client.resolve_instrument(request.instrument)

    def _map_order_detail(self, detail: dict[str, Any]) -> Order | None:
        """Map a raw order detail dict to a domain Order."""
        if not detail:
            return None
        # Use the public resolve_instrument method rather than reaching into
        # private adapter internals (_resolver).  The broker protocol exposes
        # resolve_instrument() for exactly this purpose.
        exchange = Exchange.NSE
        try:
            resolved = self._client.resolve_instrument(
                detail.get("tradingSymbol", "")
            )
            if resolved is not None:
                exchange = resolved.exchange
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            logger.warning(
                "resolve_instrument_failed: symbol=%r error=%s",
                detail.get("tradingSymbol"),
                exc,
            )
        return Order(
            order_id=detail.get("orderId", ""),
            symbol=detail.get("tradingSymbol", detail.get("symbol", "")),
            exchange=exchange,
            side=OrderSide(detail.get("transactionType", "BUY")),
            order_type=OrderType(detail.get("orderType", "LIMIT")),
            quantity=int(detail.get("quantity", 0)),
            price=Decimal(str(detail.get("price", 0))),
            state=_safe_order_state(detail.get("status", "PENDING")),
            product_type=detail.get("productType", "INTRADAY"),
            validity=detail.get("validity", "DAY"),
            trigger_price=Decimal(str(detail.get("triggerPrice", 0))),
            filled_quantity=int(detail.get("filledQty", 0)),
            avg_price=Decimal(str(detail.get("avgPrice", 0))),
        )
