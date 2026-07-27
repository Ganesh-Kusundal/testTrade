"""Round-trip tests: serialize → deserialize must yield equal domain objects.

Regression for C6: Fill was reconstructed with nonexistent kwargs
(exchange=, fill_timestamp=) and Order with price=None, so every
FillReceived/OrderPlaced replay silently degraded to a raw dict.
"""
from datetime import datetime, timezone
from decimal import Decimal

from scalpr.domain.events import FillReceived, OrderPlaced
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.observability.event_store import _deserialize_event, _serialize_event

TS = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


def test_fill_received_roundtrip() -> None:
    fill = Fill(
        fill_id="F1",
        order_id="O1",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        price=Decimal("2500.50"),
        timestamp=TS,
    )
    event = FillReceived(timestamp=TS, fill=fill)

    restored = _deserialize_event(_serialize_event(event))

    assert isinstance(restored, FillReceived)
    assert isinstance(restored.fill, Fill), "fill degraded to raw dict"
    assert restored.fill == fill


def test_order_placed_roundtrip() -> None:
    order = Order(
        order_id="O1",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        price=Decimal("2500.50"),
        state=OrderState.PENDING,
    )
    event = OrderPlaced(timestamp=TS, order=order)

    restored = _deserialize_event(_serialize_event(event))

    assert isinstance(restored, OrderPlaced)
    assert isinstance(restored.order, Order), "order degraded to raw dict"
    assert restored.order.order_id == order.order_id
    assert restored.order.price == order.price
    assert restored.order.state == order.state


def test_order_placed_roundtrip_market_order_no_price() -> None:
    # price omitted/falsy in payload must never reconstruct as None
    order = Order(
        order_id="O2",
        symbol="TCS",
        exchange=Exchange.NSE,
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=5,
    )
    event = OrderPlaced(timestamp=TS, order=order)

    restored = _deserialize_event(_serialize_event(event))

    assert isinstance(restored.order, Order)
    assert restored.order.price == Decimal("0")
