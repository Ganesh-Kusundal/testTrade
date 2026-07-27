import pytest
from decimal import Decimal
from datetime import datetime, timezone, date

# We import from scalpr.domain, which will fail initially
from scalpr.domain.instrument import Instrument, Exchange, Segment, OptionType
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.fill import Fill, PartialFill
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.domain.tick import Tick, OHLCV
from scalpr.domain.events import OrderPlaced, FillReceived


def test_order_state_invalid_transition_raises():
    """OrderState FSM with validated transitions raises ValueError on invalid moves."""
    order = Order(
        order_id="ord_100",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10,
        price=Decimal("2500.50"),
        state=OrderState.PENDING,
    )
    
    # Valid transition: PENDING -> OPEN
    opened_order = order.transition_to(OrderState.OPEN)
    assert opened_order.state == OrderState.OPEN
    
    # Valid transition: OPEN -> PARTIALLY_FILLED
    partial_order = opened_order.transition_to(OrderState.PARTIALLY_FILLED)
    assert partial_order.state == OrderState.PARTIALLY_FILLED
    
    # Valid transition: PARTIALLY_FILLED -> FILLED
    filled_order = partial_order.transition_to(OrderState.FILLED)
    assert filled_order.state == OrderState.FILLED
    
    # Invalid transition: FILLED -> OPEN should raise ValueError
    with pytest.raises(ValueError, match="Invalid transition"):
        filled_order.transition_to(OrderState.OPEN)
        
    # Invalid transition: CANCELLED -> FILLED should raise ValueError
    cancelled_order = opened_order.transition_to(OrderState.CANCELLED)
    with pytest.raises(ValueError, match="Invalid transition"):
        cancelled_order.transition_to(OrderState.FILLED)


def test_fill_price_is_decimal_not_float():
    """All prices must be Decimal. Passing float raises TypeError."""
    # Valid construction
    fill = Fill(
        fill_id="fill_001",
        order_id="ord_100",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        price=Decimal("2500.50"),
    )
    assert isinstance(fill.price, Decimal)
    assert fill.price == Decimal("2500.50")
    
    # Invalid construction with float price
    with pytest.raises(TypeError, match="price must be Decimal"):
        Fill(
            fill_id="fill_001",
            order_id="ord_100",
            symbol="RELIANCE",
            side=OrderSide.BUY,
            quantity=10,
            price=2500.50,  # type: ignore
        )


def test_tick_delta_volume_separate_from_cumulative():
    """Tick delta_volume is separate from cumulative_volume."""
    tick = Tick(
        symbol="RELIANCE",
        ltp=Decimal("2500.50"),
        bid=Decimal("2500.00"),
        ask=Decimal("2501.00"),
        delta_volume=15,
        cumulative_volume=10000,
        exchange_timestamp=datetime(2026, 6, 23, 10, 0, 0, tzinfo=timezone.utc),
    )
    assert tick.delta_volume == 15
    assert tick.cumulative_volume == 10000
    assert tick.delta_volume != tick.cumulative_volume


def test_instrument_tick_size_decimal_precision():
    """Instrument tick_size preserves exact Decimal precision."""
    inst = Instrument(
        symbol="NIFTY26JUN22000CE",
        exchange=Exchange.NSE,
        segment=Segment.OPTIONS,
        security_id="12345",
        lot_size=50,
        tick_size=Decimal("0.05"),
        option_type=OptionType.CE,
        strike=Decimal("22000.00"),
        expiry=date(2026, 6, 26),
    )
    assert isinstance(inst.tick_size, Decimal)
    assert inst.tick_size == Decimal("0.05")
    # Verify exact comparison without float conversion issues
    assert inst.tick_size != Decimal("0.050000000001")


def test_ohlcv_bar_boundary_is_utc():
    """OHLCV bar boundary open time is stored in UTC timezone-aware format."""
    utc_now = datetime.now(timezone.utc)
    bar = OHLCV(
        open=Decimal("2500.00"),
        high=Decimal("2510.00"),
        low=Decimal("2490.00"),
        close=Decimal("2505.00"),
        volume=5000,
        bar_open_time=utc_now,
        is_closed=True,
    )
    assert bar.bar_open_time.tzinfo == timezone.utc
    
    # Passing naive datetime should raise ValueError or TypeError
    naive_dt = datetime.now()
    with pytest.raises(ValueError, match="timezone-aware"):
        OHLCV(
            open=Decimal("2500.00"),
            high=Decimal("2510.00"),
            low=Decimal("2490.00"),
            close=Decimal("2505.00"),
            volume=5000,
            bar_open_time=naive_dt,
            is_closed=True,
        )


def test_position_pnl_calculation():
    """Position PnL is calculated correctly using Decimal only."""
    pos = Position(
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        quantity=10,
        avg_price=Decimal("2500.00"),
        ltp=Decimal("2500.00"),
        unrealised_pnl=Decimal("0"),
        realised_pnl=Decimal("0"),
        position_side=PositionSide.LONG,
        state=PositionState.OPEN,
    )
    
    # Unrealised PnL recalculation on LTP change
    updated_ltp = pos.with_ltp(Decimal("2510.50"))
    assert updated_ltp.unrealised_pnl == Decimal("105.00")  # (2510.50 - 2500.00) * 10
    
    # Realised PnL on partial exit (sell 5 at 2520.00)
    # Position with_fill returns new Position state
    updated_fill = updated_ltp.with_fill(quantity=-5, price=Decimal("2520.00"), side=OrderSide.SELL)
    assert updated_fill.quantity == 5
    assert updated_fill.realised_pnl == Decimal("100.00")  # (2520.00 - 2500.00) * 5
    assert updated_fill.unrealised_pnl == Decimal("100.00")  # (2520.00 - 2500.00) * 5
