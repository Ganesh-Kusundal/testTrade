import os
import tempfile
from decimal import Decimal

import pytest

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.oms.order_manager import OrderManager
from scalpr.oms.paper_oms import PaperOms
from scalpr.oms.persistence import OmsRepository
from scalpr.risk.circuit_breaker import CircuitBreaker
from scalpr.risk.position_sizer import AtrPositionSizer
from scalpr.risk.pre_trade import PreTradeRiskGate
from scalpr.risk.session_guard import SessionGuard


def test_order_manager_fill_accumulation():
    """OrderManager accumulates partial fills and transitions order to FILLED once completed."""
    om = OrderManager()

    order = Order(
        order_id="ord_1",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        price=Decimal("2500.00"),
        state=OrderState.OPEN,
    )
    om.add_order(order)

    # First partial fill (3 shares)
    f1 = Fill("f1", "ord_1", "RELIANCE", OrderSide.BUY, 3, Decimal("2499.00"))
    ord_state1 = om.process_fill(f1)
    assert ord_state1.state == OrderState.PARTIALLY_FILLED
    assert ord_state1.filled_quantity == 3
    assert ord_state1.avg_price == Decimal("2499.00")

    # Second partial fill completing the order (7 shares)
    f2 = Fill("f2", "ord_1", "RELIANCE", OrderSide.BUY, 7, Decimal("2501.00"))
    ord_state2 = om.process_fill(f2)
    assert ord_state2.state == OrderState.FILLED
    assert ord_state2.filled_quantity == 10
    # Weighted average: (3 * 2499 + 7 * 2501) / 10 = 2500.40
    assert ord_state2.avg_price == Decimal("2500.40")


def test_oms_repository_save_restore():
    """OmsRepository correctly persists and restores orders and positions in SQLite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "oms_test.db")
        repo = OmsRepository(db_path)

        order = Order(
            order_id="ord_test",
            symbol="TCS",
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=50,
            price=Decimal("3500.00"),
            state=OrderState.OPEN,
        )
        repo.save_order(order)

        pos = Position(
            symbol="TCS",
            exchange=Exchange.NSE,
            quantity=-50,
            avg_price=Decimal("3500.00"),
            ltp=Decimal("3480.00"),
            unrealised_pnl=Decimal("1000.00"),
            realised_pnl=Decimal("0.00"),
            position_side=PositionSide.SHORT,
            state=PositionState.OPEN,
        )
        repo.save_position(pos)

        # Restore from DB
        restored_orders = repo.restore_orders()
        assert "ord_test" in restored_orders
        assert restored_orders["ord_test"].symbol == "TCS"
        assert restored_orders["ord_test"].quantity == 50
        assert restored_orders["ord_test"].price == Decimal("3500.00")

        restored_positions = repo.restore_positions()
        assert "TCS" in restored_positions
        assert restored_positions["TCS"].quantity == -50
        assert restored_positions["TCS"].avg_price == Decimal("3500.00")
        assert restored_positions["TCS"].position_side == PositionSide.SHORT


def test_paper_oms_drawdown_calculation():
    """PaperOms executes fills and tracks current drawdown based on mark-to-market prices."""
    oms = PaperOms(initial_balance=Decimal("100000.00"))

    # 1. Place a long order of 10 shares of RELIANCE at 2500.00
    order = Order(
        order_id="p_ord_1",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
        price=Decimal("2500.00"),
    )

    # Simulate feed price
    oms.set_last_price("RELIANCE", Decimal("2500.00"))
    oms.place_order(order)

    # Current cash: 100000 - 10 * 2500.05 (with default 1 tick slippage) = 74999.50
    assert oms.balance == Decimal("74999.50")

    # Mark price down to 2400.00
    oms.set_last_price("RELIANCE", Decimal("2400.00"))

    # Portfolio value: 74999.50 + 10 * (2400 - 2500.05) = 74999.50 + (-1000.50) = 73999.00
    # Peak balance: 100000.00
    # Drawdown: (100000 - 73999) / 100000 = 0.26001 (26%)
    assert oms.drawdown == pytest.approx(Decimal("0.26001"), rel=1e-4)


def test_pre_trade_risk_gate():
    """PreTradeRiskGate validates max positions, capital risk limit, and concentration limits."""
    gate = PreTradeRiskGate(
        portfolio_value=Decimal("100000.00"),
        max_open_positions=2,
    )

    # Order exceeding 1% of portfolio notional (capital risk check)
    order_too_large = Order(
        order_id="large",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=100,
        price=Decimal("2500.00"),  # Notional: 250,000 > 1,000 (1% of 100k)
    )
    allowed, reason = gate.check_order(order_too_large, [], Decimal("100000"), Decimal("0"), Decimal("0"))
    assert not allowed
    assert "exceeds max notional limit" in reason

    # Order passing pre-trade risk
    order_ok = Order(
        order_id="ok",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=3,
        price=Decimal("250.00"),  # Notional: 750 < 1000
    )
    allowed, reason = gate.check_order(order_ok, [], Decimal("100000"), Decimal("100"), Decimal("0"))
    assert allowed


def test_session_guard_loss_tripping():
    """SessionGuard registers consecutive losses and triggers square off when reaching threshold."""
    from scalpr.simulation.simulated_gateway import SimulatedGateway

    gateway = SimulatedGateway(starting_capital=Decimal("100000"))
    guard = SessionGuard(gateway=gateway, max_losses=3)

    # 1. Success resets loss count
    guard.record_pnl(Decimal("100.00"))
    assert guard.consecutive_losses == 0

    # 2. 3 consecutive losses trips guard
    guard.record_pnl(Decimal("-50.00"))
    guard.record_pnl(Decimal("-20.00"))
    assert guard.consecutive_losses == 2
    assert not guard.halted

    guard.record_pnl(Decimal("-10.00"))
    assert guard.consecutive_losses == 3
    assert guard.halted


def test_atr_position_sizer():
    """AtrPositionSizer computes contract lot size aligned trading quantity based on ATR."""
    sizer = AtrPositionSizer(max_quantity_cap=1000)

    # Portfolio value: 100,000 => Risk amount: 1,000 (1%)
    # ATR: 5.00, multiplier: 2.00, lot_size: 50
    # Risk per lot: 5.00 * 2.00 * 50 = 500
    # Number of lots: 1000 / 500 = 2 lots
    # Aligned quantity: 2 * 50 = 100 shares
    qty = sizer.calculate_quantity(
        portfolio_value=Decimal("100000.00"),
        atr=Decimal("5.00"),
        multiplier=Decimal("2.00"),
        lot_size=50,
    )
    assert qty == 100
    assert isinstance(qty, int)


def test_circuit_breaker_limits():
    """CircuitBreaker trips on exceeding daily loss or drawdown limits and halts all execution."""
    cb = CircuitBreaker(daily_loss_limit_pct=0.03, drawdown_limit_pct=0.05)

    # 1. Passed check
    assert cb.check_limits(
        portfolio_value=Decimal("100000.00"),
        daily_loss=Decimal("1000.00"),  # 1%
        drawdown=Decimal("0.02"),        # 2%
    )
    assert not cb.is_tripped

    # 2. Exceeding daily loss trips breaker
    assert not cb.check_limits(
        portfolio_value=Decimal("100000.00"),
        daily_loss=Decimal("3500.00"),  # 3.5% > 3%
        drawdown=Decimal("0.02"),
    )
    assert cb.is_tripped

    # 3. Requires manual reset
    cb.reset()
    assert not cb.is_tripped

    # 4. Exceeding drawdown trips breaker
    assert not cb.check_limits(
        portfolio_value=Decimal("100000.00"),
        daily_loss=Decimal("500.00"),
        drawdown=Decimal("0.06"),        # 6% > 5%
    )
    assert cb.is_tripped
