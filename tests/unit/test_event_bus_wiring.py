"""Integration tests for event bus wiring in production flow."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, Mock

from scalpr.domain.events import (
    InMemoryEventBus,
    TickReceived,
    OrderPlaced,
    FillReceived,
    PositionUpdated,
    CircuitBreakerTripped,
    RiskCheckFailed,
)
from scalpr.domain.tick import Tick
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position, PositionSide
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.execution.order_router import OrderRouter, RiskCheckFailed as RiskCheckFailedEx, CircuitBreakerTripped as CircuitBreakerTrippedEx
from scalpr.risk.pre_trade import PreTradeRiskGate
from scalpr.risk.circuit_breaker import CircuitBreaker
from scalpr.oms.paper_oms import PaperOms


class TestEventBusWiring:
    """Test that events are properly published through the production flow."""

    def test_tick_received_event_published(self):
        """Verify TickReceived event is published when tick callback fires."""
        event_bus = InMemoryEventBus()
        received_events = []
        
        def on_tick(event: TickReceived):
            received_events.append(event)
        
        event_bus.subscribe(TickReceived, on_tick)
        
        # Simulate tick callback
        tick = Tick(
            symbol="RELIANCE",
            ltp=Decimal("2935.40"),
            bid=Decimal("2935.35"),
            ask=Decimal("2935.45"),
            delta_volume=100,
            cumulative_volume=1250000,
            exchange_timestamp=datetime.now(timezone.utc),
        )
        
        event_bus.publish(TickReceived(
            timestamp=datetime.now(timezone.utc),
            tick=tick,
        ))
        
        assert len(received_events) == 1
        assert received_events[0].tick.symbol == "RELIANCE"
        assert received_events[0].tick.ltp == Decimal("2935.40")

    def test_order_placed_event_published(self):
        """Verify OrderPlaced event is published when order passes risk checks."""
        event_bus = InMemoryEventBus()
        received_events = []
        
        def on_order(event: OrderPlaced):
            received_events.append(event)
        
        def on_fill(event: FillReceived):
            received_events.append(event)
        
        def on_position(event: PositionUpdated):
            received_events.append(event)
        
        event_bus.subscribe(OrderPlaced, on_order)
        event_bus.subscribe(FillReceived, on_fill)
        event_bus.subscribe(PositionUpdated, on_position)
        
        # Setup OrderRouter with event_bus
        paper_oms = PaperOms(event_bus=event_bus)
        risk_gate = PreTradeRiskGate()
        circuit_breaker = CircuitBreaker()
        order_router = OrderRouter(
            gateway=paper_oms,
            risk_gate=risk_gate,
            circuit_breaker=circuit_breaker,
            event_bus=event_bus,
        )
        
        # Set price for symbol
        paper_oms.set_last_price("RELIANCE", Decimal("2935.40"))
        
        # Create order
        order = Order(
            order_id="test_order_001",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            price=Decimal("2935.40"),
            state=OrderState.PENDING,
        )
        
        # Submit order through router
        fill = order_router.submit_order(
            order=order,
            positions=[],
            available_margin=Decimal("1000000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )
        
        # Verify OrderPlaced event was published
        order_events = [e for e in received_events if isinstance(e, OrderPlaced)]
        assert len(order_events) == 1
        assert order_events[0].order.order_id == "test_order_001"
        assert order_events[0].order.symbol == "RELIANCE"
        
        # Verify FillReceived and PositionUpdated were also published by PaperOms
        fill_events = [e for e in received_events if isinstance(e, FillReceived)]
        position_events = [e for e in received_events if isinstance(e, PositionUpdated)]
        
        assert len(fill_events) == 1
        assert len(position_events) == 1

    def test_circuit_breaker_event_published(self):
        """Verify CircuitBreakerTripped event is published when limits exceeded."""
        event_bus = InMemoryEventBus()
        received_events = []
        
        def on_cb(event: CircuitBreakerTripped):
            received_events.append(event)
        
        event_bus.subscribe(CircuitBreakerTripped, on_cb)
        
        # Setup OrderRouter
        paper_oms = PaperOms(event_bus=event_bus)
        risk_gate = PreTradeRiskGate()
        circuit_breaker = CircuitBreaker(daily_loss_limit_pct=0.03)  # 3% limit
        order_router = OrderRouter(
            gateway=paper_oms,
            risk_gate=risk_gate,
            circuit_breaker=circuit_breaker,
            event_bus=event_bus,
        )
        
        paper_oms.set_last_price("RELIANCE", Decimal("2935.40"))
        
        order = Order(
            order_id="test_order_002",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            price=Decimal("2935.40"),
            state=OrderState.PENDING,
        )
        
        # Submit with excessive daily loss (should trip circuit breaker)
        try:
            order_router.submit_order(
                order=order,
                positions=[],
                available_margin=Decimal("1000000"),
                daily_loss=Decimal("50000"),  # 5% loss on 1M portfolio
                portfolio_value=Decimal("1000000"),
            )
            assert False, "Should have raised CircuitBreakerTrippedEx"
        except CircuitBreakerTrippedEx:
            pass
        
        # Verify CircuitBreakerTripped event was published
        assert len(received_events) == 1
        assert received_events[0].component == "OrderRouter"
        assert "Daily loss limit exceeded" in received_events[0].reason

    def test_risk_check_failed_event_published(self):
        """Verify RiskCheckFailed event is published when pre-trade check fails."""
        event_bus = InMemoryEventBus()
        received_events = []
        
        def on_risk(event: RiskCheckFailed):
            received_events.append(event)
        
        event_bus.subscribe(RiskCheckFailed, on_risk)
        
        # Setup OrderRouter with tight risk limits
        paper_oms = PaperOms(event_bus=event_bus)
        risk_gate = PreTradeRiskGate(max_concentration_pct=0.001)  # 0.1% max order
        circuit_breaker = CircuitBreaker()
        order_router = OrderRouter(
            gateway=paper_oms,
            risk_gate=risk_gate,
            circuit_breaker=circuit_breaker,
            event_bus=event_bus,
        )
        
        paper_oms.set_last_price("RELIANCE", Decimal("2935.40"))
        
        # Create oversized order (should fail risk check)
        order = Order(
            order_id="test_order_003",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,  # Large order
            price=Decimal("2935.40"),
            state=OrderState.PENDING,
        )
        
        # Submit order (should fail risk check)
        try:
            order_router.submit_order(
                order=order,
                positions=[],
                available_margin=Decimal("100000"),  # Small margin
                daily_loss=Decimal("0"),
                portfolio_value=Decimal("100000"),
            )
            assert False, "Should have raised RiskCheckFailedEx"
        except RiskCheckFailedEx:
            pass
        
        # Verify RiskCheckFailed event was published
        assert len(received_events) == 1
        assert received_events[0].check_name == "PreTradeRiskGate"
        assert received_events[0].order.order_id == "test_order_003"

    def test_multiple_event_subscribers(self):
        """Verify multiple subscribers can listen to the same event type."""
        event_bus = InMemoryEventBus()
        subscriber1_events = []
        subscriber2_events = []
        
        def subscriber1(event: TickReceived):
            subscriber1_events.append(event)
        
        def subscriber2(event: TickReceived):
            subscriber2_events.append(event)
        
        event_bus.subscribe(TickReceived, subscriber1)
        event_bus.subscribe(TickReceived, subscriber2)
        
        tick = Tick(
            symbol="TCS",
            ltp=Decimal("4080.50"),
            bid=Decimal("4080.45"),
            ask=Decimal("4080.55"),
            delta_volume=50,
            cumulative_volume=850000,
            exchange_timestamp=datetime.now(timezone.utc),
        )
        
        event_bus.publish(TickReceived(
            timestamp=datetime.now(timezone.utc),
            tick=tick,
        ))
        
        # Both subscribers should receive the event
        assert len(subscriber1_events) == 1
        assert len(subscriber2_events) == 1
        assert subscriber1_events[0].tick.symbol == "TCS"
        assert subscriber2_events[0].tick.symbol == "TCS"

    def test_event_immutability(self):
        """Verify events are immutable (frozen dataclasses)."""
        from dataclasses import replace
        
        tick = Tick(
            symbol="INFY",
            ltp=Decimal("1847.30"),
            bid=Decimal("1847.25"),
            ask=Decimal("1847.35"),
            delta_volume=30,
            cumulative_volume=1100000,
            exchange_timestamp=datetime.now(timezone.utc),
        )
        
        event = TickReceived(
            timestamp=datetime.now(timezone.utc),
            tick=tick,
        )
        
        # Attempting to modify should raise error
        try:
            event.tick.symbol = "MODIFIED"
            assert False, "Should not be able to modify frozen event"
        except (TypeError, AttributeError):
            pass  # Expected

    def test_full_event_flow_integration(self):
        """Test complete event flow: Tick → Order → Fill → Position."""
        event_bus = InMemoryEventBus()
        all_events = []
        
        def collect_all(event):
            all_events.append(event)
        
        # Subscribe to all event types
        event_bus.subscribe(TickReceived, collect_all)
        event_bus.subscribe(OrderPlaced, collect_all)
        event_bus.subscribe(FillReceived, collect_all)
        event_bus.subscribe(PositionUpdated, collect_all)
        
        # Setup full flow
        paper_oms = PaperOms(event_bus=event_bus)
        risk_gate = PreTradeRiskGate()
        circuit_breaker = CircuitBreaker()
        order_router = OrderRouter(
            gateway=paper_oms,
            risk_gate=risk_gate,
            circuit_breaker=circuit_breaker,
            event_bus=event_bus,
        )
        
        # 1. Simulate tick
        tick = Tick(
            symbol="RELIANCE",
            ltp=Decimal("2935.40"),
            bid=Decimal("2935.35"),
            ask=Decimal("2935.45"),
            delta_volume=100,
            cumulative_volume=1250000,
            exchange_timestamp=datetime.now(timezone.utc),
        )
        event_bus.publish(TickReceived(
            timestamp=datetime.now(timezone.utc),
            tick=tick,
        ))
        
        # 2. Set price and submit order
        paper_oms.set_last_price("RELIANCE", Decimal("2935.40"))
        
        order = Order(
            order_id="integration_test_001",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            price=Decimal("2935.40"),
            state=OrderState.PENDING,
        )
        
        order_router.submit_order(
            order=order,
            positions=[],
            available_margin=Decimal("1000000"),
            daily_loss=Decimal("0"),
            portfolio_value=Decimal("1000000"),
        )
        
        # Verify all events were published
        assert len(all_events) >= 4  # Tick, Fill, Position, Order (order may come after fill)
        
        # Verify event types are present (order may vary due to PaperOms publishing before OrderRouter)
        tick_events = [e for e in all_events if isinstance(e, TickReceived)]
        order_events = [e for e in all_events if isinstance(e, OrderPlaced)]
        fill_events = [e for e in all_events if isinstance(e, FillReceived)]
        position_events = [e for e in all_events if isinstance(e, PositionUpdated)]
        
        assert len(tick_events) == 1
        assert len(order_events) == 1
        assert len(fill_events) == 1
        assert len(position_events) == 1
        
        # Verify event data integrity
        assert tick_events[0].tick.ltp == Decimal("2935.40")
        assert order_events[0].order.order_id == "integration_test_001"
        assert fill_events[0].fill.quantity == 1
        assert position_events[0].position.quantity == 1
