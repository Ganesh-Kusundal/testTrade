from __future__ import annotations

from decimal import Decimal

from scalpr.adapters.test_helpers.fake_exchange import FakeExchange
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import PositionSide
from scalpr.domain.values import ZERO
from scalpr.engine.message_bus import MessageBus


def make_order(
    order_id: str = "o1",
    symbol: str = "TCS",
    side: OrderSide = OrderSide.BUY,
    quantity: int = 10,
    price: Decimal | None = None,
) -> Order:
    return Order(
        order_id=order_id,
        symbol=symbol,
        exchange=Exchange.NSE,
        side=side,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=price or Decimal("150.0"),
    )


class TestFakeExchangeSubmit:
    def test_submit_order_returns_fill_with_correct_fields(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = make_order()

        fill = ex.submit_order(order)

        assert isinstance(fill, Fill)
        assert fill.fill_id.startswith("fake_fill_")
        assert fill.order_id == "o1"
        assert fill.symbol == "TCS"
        assert fill.side == OrderSide.BUY
        assert fill.quantity == 10
        assert fill.price == Decimal("150.0")
        assert fill.timestamp is not None

    def test_submit_order_publishes_fill_event_on_bus(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = make_order()
        received = []

        bus.subscribe("exec.event.fill", lambda e: received.append(e))
        ex.submit_order(order)

        assert len(received) == 1
        assert received[0].order_id == "o1"

    def test_submit_order_publishes_accepted_event(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = make_order()
        received = []

        bus.subscribe("exec.event.accepted", lambda e: received.append(e))
        ex.submit_order(order)

        assert len(received) == 1
        assert received[0] == "o1"

    def test_submit_order_fills_completely(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = make_order(quantity=25)

        fill = ex.submit_order(order)

        assert fill.quantity == 25

    def test_submit_sell_order_returns_correct_side(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = make_order(side=OrderSide.SELL)

        fill = ex.submit_order(order)

        assert fill.side == OrderSide.SELL

    def test_submit_market_order_uses_default_price(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = Order(
            order_id="m1",
            symbol="TCS",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
            price=ZERO,
        )

        fill = ex.submit_order(order)

        assert fill.price > ZERO
        assert fill.quantity == 10

    def test_submit_order_via_bus_routing(self):
        bus = MessageBus()
        FakeExchange(bus)
        order = make_order()
        from scalpr.engine.execution_engine import SubmitOrder

        cmd = SubmitOrder(order=order, broker="fake")
        received = []
        bus.subscribe("exec.event.fill", lambda e: received.append(e))
        bus.publish("exec.command.submit.fake", cmd)

        assert len(received) == 1


class TestFakeExchangePosition:
    def test_get_position_after_buy(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = make_order(side=OrderSide.BUY, quantity=10)
        ex.submit_order(order)

        pos = ex.get_position("TCS")
        assert pos is not None
        assert pos.quantity == 10
        assert pos.position_side == PositionSide.LONG
        assert pos.avg_price == Decimal("150.0")

    def test_get_position_after_sell(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = make_order(side=OrderSide.SELL, quantity=5)
        ex.submit_order(order)

        pos = ex.get_position("TCS")
        assert pos is not None
        assert pos.quantity == -5
        assert pos.position_side == PositionSide.SHORT

    def test_multiple_fills_accumulate_position(self):
        bus = MessageBus()
        ex = FakeExchange(bus)

        buy1 = make_order(order_id="o1", symbol="TCS", side=OrderSide.BUY, quantity=10)
        buy2 = make_order(order_id="o2", symbol="TCS", side=OrderSide.BUY, quantity=5)
        ex.submit_order(buy1)
        ex.submit_order(buy2)

        pos = ex.get_position("TCS")
        assert pos is not None
        assert pos.quantity == 15

    def test_buy_then_sell_reduces_position(self):
        bus = MessageBus()
        ex = FakeExchange(bus)

        buy = make_order(order_id="o1", symbol="TCS", side=OrderSide.BUY, quantity=10)
        ex.submit_order(buy)
        sell = make_order(order_id="o2", symbol="TCS", side=OrderSide.SELL, quantity=4)
        ex.submit_order(sell)

        pos = ex.get_position("TCS")
        assert pos is not None
        assert pos.quantity == 6

    def test_get_position_returns_none_for_unknown(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        assert ex.get_position("UNKNOWN") is None

    def test_position_tracks_multiple_symbols(self):
        bus = MessageBus()
        ex = FakeExchange(bus)

        ex.submit_order(make_order(order_id="o1", symbol="TCS", side=OrderSide.BUY, quantity=10))
        ex.submit_order(make_order(order_id="o2", symbol="RELIANCE", side=OrderSide.BUY, quantity=5))

        tcs_pos = ex.get_position("TCS")
        rel_pos = ex.get_position("RELIANCE")
        assert tcs_pos is not None and tcs_pos.quantity == 10
        assert rel_pos is not None and rel_pos.quantity == 5


class TestFakeExchangeOrders:
    def test_get_open_orders_returns_submitted(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = make_order()
        ex.submit_order(order)

        open_orders = ex.get_open_orders()
        assert len(open_orders) == 0  # filled orders are terminal

    def test_open_orders_with_multiple_orders(self):
        bus = MessageBus()
        ex = FakeExchange(bus)

        ex.submit_order(make_order(order_id="o1"))
        ex.submit_order(make_order(order_id="o2"))
        ex.submit_order(make_order(order_id="o3"))

        assert len(ex.get_open_orders()) == 0

    def test_cancel_order_removes_from_open(self):
        bus = MessageBus()
        ex = FakeExchange(bus)

        open_order = make_order(order_id="open1")
        ex._orders["open1"] = open_order

        result = ex.cancel_order("open1")
        assert result is True

        assert "open1" in ex._orders
        assert ex._orders["open1"].state == OrderState.CANCELLED

    def test_cancel_order_returns_false_for_unknown(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        assert ex.cancel_order("nonexistent") is False

    def test_cancel_order_returns_false_for_filled(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        order = make_order()
        ex.submit_order(order)
        assert ex.cancel_order("o1") is False

    def test_cancel_order_publishes_cancelled_event(self):
        bus = MessageBus()
        ex = FakeExchange(bus)
        received = []
        bus.subscribe("exec.event.cancelled", lambda e: received.append(e))

        open_order = make_order(order_id="open1")
        ex._orders["open1"] = open_order
        ex.cancel_order("open1")

        assert len(received) == 1
