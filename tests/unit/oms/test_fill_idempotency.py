"""Fill idempotency + overfill rejection in OrderManager.process_fill.

Pins the Phase 1 money-path fix: fill_id is the idempotency key (broker
retries must not double-count), and overfills are rejected gracefully
BEFORE any state mutation — never a crash mid-update.
"""
from decimal import Decimal

import pytest

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.oms.order_manager import OrderManager


def _make_order(qty=10):
    return Order(
        order_id="ord_1", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=qty, price=Decimal("2500"), state=OrderState.PENDING,
    )


def _fill(fill_id, qty, price=Decimal("2500")):
    return Fill(fill_id, "ord_1", "RELIANCE", OrderSide.BUY, qty, price)


@pytest.fixture
def om():
    manager = OrderManager()
    manager.add_order(_make_order())
    return manager


def test_duplicate_fill_id_applied_once(om):
    """Same fill delivered twice (broker retry) must count exactly once."""
    fill = _fill("f1", 4)
    om.process_fill(fill)
    result = om.process_fill(fill)  # duplicate delivery

    assert result.filled_quantity == 4
    assert len(om.fills["ord_1"]) == 1
    assert om.get_order("ord_1").state == OrderState.PARTIALLY_FILLED


def test_duplicate_fill_id_does_not_change_avg_price(om):
    om.process_fill(_fill("f1", 4, Decimal("2500")))
    before = om.get_order("ord_1")
    after = om.process_fill(_fill("f1", 4, Decimal("2500")))
    assert after == before


def test_overfill_rejected_gracefully(om):
    """Cumulative fills > order.quantity ⇒ explicit reject, state unchanged."""
    om.process_fill(_fill("f1", 6))

    with pytest.raises(ValueError, match="[Oo]verfill"):
        om.process_fill(_fill("f2", 6))

    order = om.get_order("ord_1")
    assert order.filled_quantity == 6
    assert order.state == OrderState.PARTIALLY_FILLED
    assert len(om.fills["ord_1"]) == 1  # rejected fill not accumulated


def test_single_fill_exceeding_quantity_rejected(om):
    with pytest.raises(ValueError, match="[Oo]verfill"):
        om.process_fill(_fill("f1", 11))

    order = om.get_order("ord_1")
    assert order.filled_quantity == 0
    assert order.state == OrderState.PENDING
    assert len(om.fills.get("ord_1", [])) == 0


def test_exact_fill_still_completes(om):
    """Regression: legitimate full fill still transitions to FILLED."""
    updated = om.process_fill(_fill("f1", 10))
    assert updated.filled_quantity == 10
    assert updated.state == OrderState.FILLED
