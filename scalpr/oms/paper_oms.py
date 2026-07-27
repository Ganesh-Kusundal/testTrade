from __future__ import annotations

import threading
from datetime import datetime, timezone
from decimal import Decimal

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.domain.fill import Fill
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.domain.events import FillReceived, PositionUpdated, IEventBus


class PaperOms(IBrokerGateway):
    """Paper Trading OMS simulating order executions, slippage, and tracking paper portfolio metrics."""

    def __init__(
        self,
        initial_balance: Decimal = Decimal("1000000.00"),
        default_tick_size: Decimal = Decimal("0.05"),
        slippage_ticks: int = 1,
        event_bus: IEventBus | None = None,
    ) -> None:
        self.balance = initial_balance
        self.peak_balance = initial_balance
        self.positions_dict: dict[str, Position] = {}
        self.orders_dict: dict[str, Order] = {}
        self.last_prices: dict[str, Decimal] = {}

        self.default_tick_size = default_tick_size
        self.slippage_ticks = slippage_ticks
        self._lock = threading.RLock()
        self._connected = True
        self.event_bus = event_bus

    def set_last_price(self, symbol: str, price: Decimal) -> None:
        """Update last known price (used for market fills and mark-to-market)."""
        with self._lock:
            self.last_prices[symbol] = price
            pos = self.positions_dict.get(symbol)
            if pos:
                self.positions_dict[symbol] = pos.with_ltp(price)
                self._recalculate_peak_drawdown()

    def place_order(self, order: Order) -> Fill:
        with self._lock:
            if order.order_id in self.orders_dict:
                raise ValueError(f"Duplicate order ID: {order.order_id}")

            symbol = order.symbol
            last_price = self.last_prices.get(symbol, order.price or Decimal("2500.00"))
            tick_size = self.default_tick_size

            # Execution Price calculation (Slippage Model)
            if order.order_type == OrderType.MARKET:
                slippage = tick_size * Decimal(self.slippage_ticks)
                execution_price = last_price + slippage if order.side == OrderSide.BUY else last_price - slippage
            else:
                execution_price = order.price

            # Check if execution makes sense
            if execution_price <= 0:
                raise ValueError(f"Invalid execution price: {execution_price}")

            # Register order as filled
            filled_order = replace_order_state(order, OrderState.FILLED, filled_qty=order.quantity, avg_price=execution_price)
            self.orders_dict[order.order_id] = filled_order

            # Generate Fill
            fill = Fill(
                fill_id=f"p_fill_{order.order_id}",
                order_id=order.order_id,
                symbol=symbol,
                side=order.side,
                quantity=order.quantity,
                price=execution_price,
                timestamp=datetime.now(timezone.utc),
            )

            # Update position
            current_pos = self.positions_dict.get(symbol)
            if current_pos is None:
                current_pos = Position(
                    symbol=symbol,
                    exchange=order.exchange,
                    quantity=0,
                    avg_price=Decimal("0"),
                    ltp=execution_price,
                    unrealised_pnl=Decimal("0"),
                    realised_pnl=Decimal("0"),
                    position_side=PositionSide.FLAT,
                    state=PositionState.FLAT,
                )

            # Apply fill
            # Signed quantity logic for Position.with_fill: BUY is positive, SELL is negative
            signed_qty = order.quantity if order.side == OrderSide.BUY else -order.quantity
            previous_quantity = current_pos.quantity
            updated_pos = current_pos.with_fill(signed_qty, execution_price, order.side)
            self.positions_dict[symbol] = updated_pos

            # Update cash balance
            transaction_value = execution_price * Decimal(order.quantity)
            if order.side == OrderSide.BUY:
                self.balance -= transaction_value
            else:
                self.balance += transaction_value

            self._recalculate_peak_drawdown()
            
            # Publish FillReceived event
            if self.event_bus:
                self.event_bus.publish(
                    FillReceived(
                        timestamp=datetime.now(timezone.utc),
                        fill=fill,
                    )
                )
            
            # Publish PositionUpdated event if quantity changed
            if self.event_bus and updated_pos.quantity != previous_quantity:
                self.event_bus.publish(
                    PositionUpdated(
                        timestamp=datetime.now(timezone.utc),
                        position=updated_pos,
                        previous_quantity=previous_quantity,
                    )
                )
            
            return fill

    def modify_order(self, order_id: str, price: Decimal, quantity: int) -> bool:
        # In paper OMS, orders fill immediately, so modifying them is generally too late.
        return False

    def cancel_order(self, order_id: str) -> bool:
        return False

    def get_order_status(self, order_id: str) -> Order:
        with self._lock:
            order = self.orders_dict.get(order_id)
            if not order:
                raise ValueError(f"Order not found: {order_id}")
            return order

    def get_positions(self) -> list[Position]:
        with self._lock:
            return list(self.positions_dict.values())

    def get_margins(self) -> dict:
        with self._lock:
            return {"available_margin": self.balance}

    def is_connected(self) -> bool:
        return self._connected

    def square_off_all(self) -> list[Fill]:
        with self._lock:
            fills = []
            for symbol, pos in list(self.positions_dict.items()):
                if pos.quantity != 0:
                    side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY
                    order = Order(
                        order_id=f"p_sq_{symbol}_{int(datetime.now(timezone.utc).timestamp())}",
                        symbol=symbol,
                        exchange=pos.exchange,
                        side=side,
                        order_type=OrderType.MARKET,
                        quantity=abs(pos.quantity),
                        price=pos.ltp,
                        state=OrderState.PENDING,
                    )
                    fill = self.place_order(order)
                    fills.append(fill)
            return fills

    @property
    def daily_pnl(self) -> Decimal:
        """Calculate aggregate PnL (realised + unrealised) across all positions."""
        with self._lock:
            return sum(((pos.realised_pnl + pos.unrealised_pnl) for pos in self.positions_dict.values()), Decimal("0"))

    @property
    def drawdown(self) -> Decimal:
        """Current drawdown from peak balance."""
        with self._lock:
            portfolio_value = self.balance + sum((pos.unrealised_pnl for pos in self.positions_dict.values()), Decimal("0"))
            if self.peak_balance <= 0:
                return Decimal("0")
            dd = (self.peak_balance - portfolio_value) / self.peak_balance
            return max(Decimal("0"), dd)

    def _recalculate_peak_drawdown(self) -> None:
        portfolio_value = self.balance + sum((pos.unrealised_pnl for pos in self.positions_dict.values()), Decimal("0"))
        if portfolio_value > self.peak_balance:
            self.peak_balance = portfolio_value


def replace_order_state(order: Order, new_state: OrderState, filled_qty: int, avg_price: Decimal) -> Order:
    from dataclasses import replace
    return replace(order, state=new_state, filled_quantity=filled_qty, avg_price=avg_price)
