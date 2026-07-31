from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from scalpr.domain.events import FillReceived, OrderPlaced
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.engine.clock import StaticClock
from scalpr.engine.execution_engine import (
    Cache,
    CancelOrder,
    EventStore,
    ExecutionEngine,
    ModifyOrder,
    OrderAccepted,
    OrderCancelled,
    OrderCancelRejected,
    OrderFilled,
    OrderModified,
    OrderModifyRejected,
    OrderRejected,
    SubmitOrder,
)
from scalpr.engine.message_bus import MessageBus


def make_order(
    order_id: str = "o1",
    symbol: str = "TCS",
    side: OrderSide = OrderSide.BUY,
    quantity: int = 10,
    price: Decimal | None = None,
    state: OrderState = OrderState.PENDING,
) -> Order:
    return Order(
        order_id=order_id,
        symbol=symbol,
        exchange=Exchange.NSE,
        side=side,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=price or Decimal("150.0"),
        state=state,
    )


def make_fill(
    order_id: str = "o1",
    symbol: str = "TCS",
    side: OrderSide = OrderSide.BUY,
    quantity: int = 10,
    price: Decimal | None = None,
) -> Fill:
    return Fill(
        fill_id="f1",
        order_id=order_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price or Decimal("150.0"),
        timestamp=datetime.now(timezone.utc),
    )


class TestExecutionEngineStart:
    def test_start_subscribes_to_broker_specific_topics(self):
        """Engine must subscribe to broker-specific event topics, not generic ones."""
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        # Verify engine subscribed to broker-specific topics
        assert "exec.event.accepted.dhan" in bus._subscribers
        assert "exec.event.filled.dhan" in bus._subscribers
        assert "exec.event.rejected.dhan" in bus._subscribers
        assert "exec.event.cancelled.dhan" in bus._subscribers

    def test_start_subscribes_and_routes_submit(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        routed = []

        bus.subscribe("exec.command.submit.fake", lambda e: routed.append(e))
        order = make_order()
        cmd = SubmitOrder(order=order, broker="fake")
        bus.publish("exec.command.submit", cmd)

        assert len(routed) == 1
        assert routed[0].order.order_id == "o1"

    def test_start_subscribes_and_routes_cancel(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        routed = []

        order = make_order(order_id="o1")
        engine.cache.update(order)
        bus.subscribe("exec.command.cancel.fake", lambda e: routed.append(e))
        cmd = CancelOrder(order_id="o1", broker="fake")
        bus.publish("exec.command.cancel", cmd)

        assert len(routed) == 1
        assert routed[0].order_id == "o1"

    def test_start_subscribes_and_routes_modify(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        routed = []

        order = make_order(order_id="o1")
        engine.cache.update(order)
        bus.subscribe("exec.command.modify.fake", lambda e: routed.append(e))
        cmd = ModifyOrder(order_id="o1", updates={"price": Decimal("160.0")}, broker="fake")
        bus.publish("exec.command.modify", cmd)

        assert len(routed) == 1
        assert routed[0].order_id == "o1"

    def test_topic_routing_by_broker_suffix(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        dhan_routed = []
        fake_routed = []

        bus.subscribe("exec.command.submit.dhan", lambda e: dhan_routed.append(e))
        bus.subscribe("exec.command.submit.fake", lambda e: fake_routed.append(e))

        order_dhan = make_order(order_id="o1")
        order_fake = make_order(order_id="o2")

        bus.publish("exec.command.submit", SubmitOrder(order=order_dhan, broker="dhan"))
        bus.publish("exec.command.submit", SubmitOrder(order=order_fake, broker="fake"))

        assert len(dhan_routed) == 1
        assert len(fake_routed) == 1

    def test_stop_does_not_crash(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        engine.stop()

class TestExecutionEngineFSM:
    def test_submit_transitions_to_pending_in_cache(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1")
        cmd = SubmitOrder(order=order, broker="fake")
        bus.publish("exec.command.submit", cmd)

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.state == OrderState.PENDING

    def test_accepted_transitions_to_open(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1")
        cmd = SubmitOrder(order=order, broker="dhan")
        bus.publish("exec.command.submit", cmd)
        bus.publish("exec.event.accepted.dhan", OrderAccepted(order_id="o1", timestamp=clock.utc_now()))

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.state == OrderState.OPEN

    def test_fill_transitions_to_filled(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1")
        cmd = SubmitOrder(order=order, broker="dhan")
        bus.publish("exec.command.submit", cmd)

        fill = make_fill(order_id="o1", quantity=10)
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="o1", fill=fill, timestamp=clock.utc_now()))

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.state == OrderState.FILLED
        assert cached.filled_quantity == 10

    def test_fsm_rejects_cancel_after_filled(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1")
        cmd = SubmitOrder(order=order, broker="dhan")
        bus.publish("exec.command.submit", cmd)
        fill = make_fill(order_id="o1", quantity=10)
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="o1", fill=fill, timestamp=clock.utc_now()))

        cancel_cmd = CancelOrder(order_id="o1", broker="dhan")
        bus.publish("exec.command.cancel", cancel_cmd)

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.state == OrderState.FILLED

    def test_fsm_rejects_modify_after_filled(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1")
        cmd = SubmitOrder(order=order, broker="dhan")
        bus.publish("exec.command.submit", cmd)
        fill = make_fill(order_id="o1", quantity=10)
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="o1", fill=fill, timestamp=clock.utc_now()))

        modify_cmd = ModifyOrder(order_id="o1", updates={"price": Decimal("160.0")}, broker="dhan")
        bus.publish("exec.command.modify", modify_cmd)

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.state == OrderState.FILLED

    def test_partial_fill_transitions_to_partially_filled(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1", quantity=20)
        cmd = SubmitOrder(order=order, broker="dhan")
        bus.publish("exec.command.submit", cmd)

        fill = make_fill(order_id="o1", quantity=5)
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="o1", fill=fill, timestamp=clock.utc_now()))

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.state == OrderState.PARTIALLY_FILLED
        assert cached.filled_quantity == 5

    def test_multiple_fills_complete_order(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1", quantity=20)
        cmd = SubmitOrder(order=order, broker="dhan")
        bus.publish("exec.command.submit", cmd)

        fill1 = make_fill(order_id="o1", quantity=5)
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="o1", fill=fill1, timestamp=clock.utc_now()))
        fill2 = make_fill(order_id="o1", quantity=15)
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="o1", fill=fill2, timestamp=clock.utc_now()))

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.state == OrderState.FILLED
        assert cached.filled_quantity == 20

    def test_rejected_transitions_to_rejected(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1")
        cmd = SubmitOrder(order=order, broker="dhan")
        bus.publish("exec.command.submit", cmd)

        bus.publish("exec.event.rejected.dhan", OrderRejected(order_id="o1", reason="insufficient margin", timestamp=clock.utc_now()))

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.state == OrderState.REJECTED
        assert cached.reject_reason == "insufficient margin"

    def test_cancelled_transitions_to_cancelled(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1", state=OrderState.OPEN)
        cache_order = replace(order)
        engine.cache.update(cache_order)

        bus.publish("exec.event.cancelled.dhan", OrderCancelled(order_id="o1", timestamp=clock.utc_now()))

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.state == OrderState.CANCELLED


class TestExecutionEngineCache:
    def test_cache_stores_and_retrieves_order(self):
        cache = Cache()
        order = make_order()
        cache.update(order)

        assert cache.order("o1") is order

    def test_cache_returns_none_for_unknown_order(self):
        cache = Cache()
        assert cache.order("nonexistent") is None

    def test_cache_open_orders(self):
        cache = Cache()
        o1 = make_order(order_id="o1", state=OrderState.PENDING)
        o2 = make_order(order_id="o2", state=OrderState.FILLED)
        o3 = make_order(order_id="o3", state=OrderState.OPEN)
        cache.update(o1)
        cache.update(o2)
        cache.update(o3)

        open_orders = cache.open_orders()
        assert len(open_orders) == 2
        ids = {o.order_id for o in open_orders}
        assert ids == {"o1", "o3"}

    def test_cache_open_orders_excludes_terminal(self):
        cache = Cache()
        cache.update(make_order(order_id="o1", state=OrderState.FILLED))
        cache.update(make_order(order_id="o2", state=OrderState.CANCELLED))
        cache.update(make_order(order_id="o3", state=OrderState.REJECTED))
        assert cache.open_orders() == []

    def test_cache_all_returns_all_orders(self):
        cache = Cache()
        cache.update(make_order(order_id="o1"))
        cache.update(make_order(order_id="o2"))
        assert len(cache.all()) == 2

    def test_cache_clear_empties(self):
        cache = Cache()
        cache.update(make_order(order_id="o1"))
        cache.clear()
        assert cache.order("o1") is None


class TestExecutionEngineEventStore:
    def test_event_store_appends_and_replays_events(self):
        store = EventStore()
        ev1 = OrderAccepted(order_id="o1", timestamp=datetime(2024, 1, 1))
        ev2 = OrderFilled(
            order_id="o1",
            fill=make_fill(),
            timestamp=datetime(2024, 1, 1),
        )
        store.append(ev1)
        store.append(ev2)

        events = store.events("o1")
        assert len(events) == 2

    def test_event_store_events_filtered_by_order_id(self):
        store = EventStore()
        ev1 = OrderAccepted(order_id="o1", timestamp=datetime(2024, 1, 1))
        ev2 = OrderAccepted(order_id="o2", timestamp=datetime(2024, 1, 1))
        store.append(ev1)
        store.append(ev2)

        assert len(store.events("o1")) == 1
        assert len(store.events("o2")) == 1

    def test_event_store_clear(self):
        store = EventStore()
        store.append("event")
        store.clear()
        assert store.all() == []

    def test_event_store_all_returns_all(self):
        store = EventStore()
        store.append("a")
        store.append("b")
        assert store.all() == ["a", "b"]

    def test_event_store_events_unknown_order_id(self):
        store = EventStore()
        store.append(OrderAccepted(order_id="o1", timestamp=datetime(2024, 1, 1)))
        assert store.events("nonexistent") == []


class TestExecutionEngineDomainEvents:
    def test_engine_publishes_order_placed_on_submit(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        received = []

        bus.subscribe("domain.order.placed", lambda e: received.append(e))
        order = make_order()
        cmd = SubmitOrder(order=order, broker="fake")
        bus.publish("exec.command.submit", cmd)

        assert len(received) == 1
        assert isinstance(received[0], OrderPlaced)
        assert received[0].order.order_id == "o1"

    def test_engine_publishes_domain_fill_event(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        received = []

        bus.subscribe("domain.fill.received", lambda e: received.append(e))
        order = make_order()
        cmd = SubmitOrder(order=order, broker="dhan")
        bus.publish("exec.command.submit", cmd)

        fill = make_fill(order_id="o1", quantity=10)
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="o1", fill=fill, timestamp=clock.utc_now()))

        assert len(received) == 1
        assert isinstance(received[0], FillReceived)
        assert received[0].fill.fill_id == "f1"

    def test_domain_events_have_utc_timestamps(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        received = []

        bus.subscribe("domain.fill.received", lambda e: received.append(e))
        order = make_order()
        cmd = SubmitOrder(order=order, broker="dhan")
        bus.publish("exec.command.submit", cmd)
        fill = make_fill(order_id="o1", quantity=10)
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="o1", fill=fill, timestamp=clock.utc_now()))

        assert received[0].timestamp.tzinfo == timezone.utc


class TestExecutionEngineClock:
    def test_clock_injection_used_in_event_store_timestamps(self):
        bus = MessageBus()
        clock = StaticClock(start_time=datetime(2025, 6, 15, 10, 30, 0))
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1", state=OrderState.PENDING)
        engine.cache.update(order)
        bus.publish("exec.event.accepted.dhan", OrderAccepted(order_id="o1", timestamp=clock.utc_now()))

        events = engine.event_store.events("o1")
        accepted = [e for e in events if isinstance(e, OrderAccepted)]
        assert len(accepted) == 1
        assert accepted[0].timestamp == datetime(2025, 6, 15, 10, 30, 0)

    def test_order_filled_event_uses_clock_timestamp(self):
        bus = MessageBus()
        clock = StaticClock(start_time=datetime(2025, 6, 15, 10, 30, 0))
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1", state=OrderState.OPEN)
        engine.cache.update(order)
        fill = make_fill(order_id="o1", quantity=10)
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="o1", fill=fill, timestamp=clock.utc_now()))

        events = engine.event_store.events("o1")
        filled = [e for e in events if isinstance(e, OrderFilled)]
        assert len(filled) == 1
        assert filled[0].timestamp == datetime(2025, 6, 15, 10, 30, 0)

    def test_clock_advance_reflected_in_events(self):
        bus = MessageBus()
        clock = StaticClock(start_time=datetime(2025, 6, 15, 10, 30, 0))
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order = make_order(order_id="o1", state=OrderState.PENDING)
        engine.cache.update(order)
        clock.advance(60)
        bus.publish("exec.event.accepted.dhan", OrderAccepted(order_id="o1", timestamp=clock.utc_now()))

        events = engine.event_store.events("o1")
        accepted = [e for e in events if isinstance(e, OrderAccepted)]
        assert accepted[0].timestamp == datetime(2025, 6, 15, 10, 31, 0)


class TestExecutionEngineEdgeCases:
    def test_submit_duplicate_order_id_does_not_overwrite(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        order1 = make_order(order_id="o1", price=Decimal("150.0"))
        order2 = make_order(order_id="o1", price=Decimal("200.0"))

        bus.publish("exec.command.submit", SubmitOrder(order=order1, broker="fake"))
        bus.publish("exec.command.submit", SubmitOrder(order=order2, broker="fake"))

        cached = engine.cache.order("o1")
        assert cached is not None
        assert cached.price == Decimal("150.0")

    def test_cancel_nonexistent_order_does_not_crash(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        cmd = CancelOrder(order_id="nonexistent", broker="fake")
        bus.publish("exec.command.cancel", cmd)

    def test_modify_nonexistent_order_does_not_crash(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        cmd = ModifyOrder(order_id="nonexistent", updates={"price": Decimal("160.0")}, broker="fake")
        bus.publish("exec.command.modify", cmd)

    def test_fill_for_unknown_order_does_not_crash(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        fill = make_fill(order_id="nonexistent")
        bus.publish("exec.event.filled.dhan", OrderFilled(order_id="nonexistent", fill=fill, timestamp=clock.utc_now()))

    def test_rejected_for_unknown_order_does_not_crash(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        bus.publish("exec.event.rejected.dhan", OrderRejected(order_id="nonexistent", reason="test", timestamp=clock.utc_now()))

    def test_accepted_for_unknown_order_does_not_crash(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()

        bus.publish("exec.event.accepted.dhan", OrderAccepted(order_id="nonexistent", timestamp=clock.utc_now()))


class TestConfirmationDrivenLifecycle:
    def _open_order(self, bus, clock, engine, order_id="o1"):
        order = Order(
            order_id=order_id, symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500.00"),
        )
        bus.publish("exec.command.submit", SubmitOrder(order=order))
        bus.publish(
            "exec.event.accepted.dhan",
            OrderAccepted(order_id=order_id, timestamp=clock.utc_now(), broker_order_id="ORD1"),
        )
        assert engine.cache.order(order_id).state == OrderState.OPEN
        return order

    def _engine(self):
        bus = MessageBus()
        clock = StaticClock()
        engine = ExecutionEngine(bus, clock)
        engine.start()
        return bus, clock, engine

    def test_cancel_command_does_not_transition_before_confirmation(self):
        """Marking CANCELLED on intent means the local book says flat while the
        broker still holds a live order."""
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)

        bus.publish("exec.command.cancel", CancelOrder(order_id="o1"))

        assert engine.cache.order("o1").state == OrderState.OPEN

    def test_cancel_transitions_only_on_broker_confirmation(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)
        bus.publish("exec.command.cancel", CancelOrder(order_id="o1"))

        bus.publish("exec.event.cancelled.dhan",
                    OrderCancelled(order_id="o1", timestamp=clock.utc_now()))

        assert engine.cache.order("o1").state == OrderState.CANCELLED

    def test_cancel_rejected_leaves_order_open(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)
        bus.publish("exec.command.cancel", CancelOrder(order_id="o1"))

        bus.publish("exec.event.cancel_rejected.dhan",
                    OrderCancelRejected(order_id="o1", reason="DH-906",
                                        timestamp=clock.utc_now()))

        assert engine.cache.order("o1").state == OrderState.OPEN

    def test_modify_command_does_not_mutate_before_confirmation(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)

        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"price": Decimal("2600.00")}))

        assert engine.cache.order("o1").price == Decimal("2500.00")

    def test_modify_applies_on_confirmation(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)
        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"price": Decimal("2600.00")}))

        bus.publish("exec.event.modified.dhan",
                    OrderModified(order_id="o1", updates={"price": Decimal("2600.00")},
                                  timestamp=clock.utc_now()))

        assert engine.cache.order("o1").price == Decimal("2600.00")

    def test_modify_rejected_leaves_order_untouched(self):
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)
        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"price": Decimal("2600.00")}))

        bus.publish("exec.event.modify_rejected.dhan",
                    OrderModifyRejected(order_id="o1", reason="DH-905",
                                        timestamp=clock.utc_now()))

        assert engine.cache.order("o1").price == Decimal("2500.00")

    def test_non_whitelisted_modify_field_is_refused(self):
        """An arbitrary caller dict must not be able to rewrite the book of
        record — only price, quantity and trigger_price are modifiable."""
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)

        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"state": OrderState.FILLED}))
        bus.publish("exec.event.modified.dhan",
                    OrderModified(order_id="o1", updates={"state": OrderState.FILLED},
                                  timestamp=clock.utc_now()))

        assert engine.cache.order("o1").state == OrderState.OPEN

    def test_validity_is_whitelisted_and_applies_on_confirmation(self):
        """OrderService.modify can send validity; the engine must apply it on
        broker confirmation or the local book diverges from the broker."""
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)

        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"validity": "IOC"}))
        bus.publish("exec.event.modified.dhan",
                    OrderModified(order_id="o1", updates={"validity": "IOC"},
                                  timestamp=clock.utc_now()))

        assert engine.cache.order("o1").validity == "IOC"

    def test_invalid_modify_value_is_refused_not_crashed(self):
        """A whitelisted key with an unusable value (e.g. quantity=0) must
        not blow up the bus publisher via an uncaught ValueError."""
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine)

        bus.publish("exec.command.modify",
                    ModifyOrder(order_id="o1", updates={"quantity": 0}))
        bus.publish("exec.event.modified.dhan",
                    OrderModified(order_id="o1", updates={"quantity": 0},
                                  timestamp=clock.utc_now()))

        cached = engine.cache.order("o1")
        assert cached.quantity == 10  # unchanged, no exception propagated

    def test_fill_uses_weighted_average_price(self):
        """avg_price drives cost basis and PnL; it must be a quantity-weighted
        average of fills, not the last marginal fill price."""
        bus, clock, engine = self._engine()
        self._open_order(bus, clock, engine, order_id="wavg")

        bus.publish(
            "exec.event.filled.dhan",
            OrderFilled(
                order_id="wavg",
                fill=make_fill(order_id="wavg", quantity=4, price=Decimal("100.00")),
                timestamp=clock.utc_now(),
            ),
        )
        bus.publish(
            "exec.event.filled.dhan",
            OrderFilled(
                order_id="wavg",
                fill=make_fill(order_id="wavg", quantity=6, price=Decimal("200.00")),
                timestamp=clock.utc_now(),
            ),
        )

        cached = engine.cache.order("wavg")
        assert cached.state == OrderState.FILLED
        assert cached.filled_quantity == 10
        # (4*100 + 6*200) / 10 = 160.00
        assert cached.avg_price == Decimal("160.00")
