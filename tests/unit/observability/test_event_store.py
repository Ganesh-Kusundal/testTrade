"""Tests for EventStore and replay integration."""
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from scalpr.domain.events import (
    CircuitBreakerTripped,
    OrderPlaced,
    TickReceived,
)
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.tick import Tick
from scalpr.observability.event_store import EventStore
from scalpr.simulation.replay_engine import ReplayEngine


class TestEventStore:
    """Test EventStore persistence and retrieval."""

    @pytest.fixture
    def event_store(self):
        """Create temporary event store for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_events.db"
            store = EventStore(db_path=db_path)
            yield store

    def _create_tick_event(self, symbol: str = "RELIANCE") -> TickReceived:
        return TickReceived(
            timestamp=datetime.now(timezone.utc),
            tick=Tick(
                symbol=symbol,
                ltp=Decimal("2935.40"),
                bid=Decimal("2935.35"),
                ask=Decimal("2935.45"),
                delta_volume=100,
                cumulative_volume=1000,
                exchange_timestamp=datetime.now(timezone.utc),
            )
        )

    def _create_order_event(self, order_id: str = "ord_1") -> OrderPlaced:
        return OrderPlaced(
            timestamp=datetime.now(timezone.utc),
            order=Order(
                order_id=order_id,
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100,
                price=Decimal("2935.00"),
                state=OrderState.OPEN,
            )
        )

    def test_append_and_retrieve_single_event(self, event_store):
        """Test basic event append and retrieve."""
        event = self._create_tick_event()
        seq = event_store.append(event, session_id="test_session")

        assert seq == 1  # First event (1-indexed)
        assert event_store.get_event_count("test_session") == 1

        events = event_store.get_session_events("test_session")
        assert len(events) == 1

        retrieved_seq, retrieved_event = events[0]
        assert retrieved_seq == 1
        assert isinstance(retrieved_event, TickReceived)
        assert retrieved_event.tick.symbol == "RELIANCE"

    def test_append_multiple_events_preserves_sequence(self, event_store):
        """Test that events maintain sequence order."""
        events_data = [
            self._create_tick_event("RELIANCE"),
            self._create_order_event("ord_1"),
            self._create_tick_event("TCS"),
        ]

        sequences = []
        for event in events_data:
            seq = event_store.append(event, session_id="test_session")
            sequences.append(seq)

        assert sequences == [1, 2, 3]

        retrieved = event_store.get_session_events("test_session")
        assert len(retrieved) == 3

        # Verify order
        assert isinstance(retrieved[0][1], TickReceived)
        assert isinstance(retrieved[1][1], OrderPlaced)
        assert isinstance(retrieved[2][1], TickReceived)

    def test_multiple_sessions_isolated(self, event_store):
        """Test that different sessions have isolated event streams."""
        event_store.append(self._create_tick_event("RELIANCE"), session_id="session_A")
        event_store.append(self._create_tick_event("TCS"), session_id="session_B")
        event_store.append(self._create_tick_event("INFY"), session_id="session_A")

        events_a = event_store.get_session_events("session_A")
        events_b = event_store.get_session_events("session_B")

        assert len(events_a) == 2
        assert len(events_b) == 1

        # Verify session A events
        assert events_a[0][1].tick.symbol == "RELIANCE"
        assert events_a[1][1].tick.symbol == "INFY"

        # Verify session B events
        assert events_b[0][1].tick.symbol == "TCS"

    def test_filter_by_event_type(self, event_store):
        """Test filtering events by type."""
        event_store.append(self._create_tick_event("RELIANCE"), session_id="test")
        event_store.append(self._create_order_event("ord_1"), session_id="test")
        event_store.append(self._create_tick_event("TCS"), session_id="test")
        event_store.append(self._create_order_event("ord_2"), session_id="test")

        # Get only tick events
        tick_events = event_store.get_session_events("test", event_type="TickReceived")
        assert len(tick_events) == 2
        assert all(isinstance(e, TickReceived) for _, e in tick_events)

        # Get only order events
        order_events = event_store.get_session_events("test", event_type="OrderPlaced")
        assert len(order_events) == 2
        assert all(isinstance(e, OrderPlaced) for _, e in order_events)

    def test_range_query(self, event_store):
        """Test retrieving events within a sequence range."""
        for i in range(10):
            event_store.append(self._create_tick_event(), session_id="test")

        # Get events 3-6 (inclusive)
        events = event_store.get_session_events("test", from_seq=3, to_seq=6)

        assert len(events) == 4
        assert events[0][0] == 3
        assert events[-1][0] == 6

    def test_get_latest_sequence(self, event_store):
        """Test getting latest sequence number."""
        assert event_store.get_latest_sequence("empty_session") == 0

        event_store.append(self._create_tick_event(), session_id="test")
        event_store.append(self._create_tick_event(), session_id="test")
        event_store.append(self._create_tick_event(), session_id="test")

        assert event_store.get_latest_sequence("test") == 3

    def test_delete_session(self, event_store):
        """Test deleting all events for a session."""
        event_store.append(self._create_tick_event(), session_id="session_A")
        event_store.append(self._create_tick_event(), session_id="session_A")
        event_store.append(self._create_tick_event(), session_id="session_B")

        count = event_store.delete_session("session_A")
        assert count == 2

        assert event_store.get_event_count("session_A") == 0
        assert event_store.get_event_count("session_B") == 1

    def test_event_round_trip_complex_event(self, event_store):
        """Test serialization/deserialization of complex events."""
        event = CircuitBreakerTripped(
            timestamp=datetime.now(timezone.utc),
            component="SessionGuard",
            reason="Max daily loss exceeded",
            threshold=10000.0,
            current_value=10500.0,
        )

        event_store.append(event, session_id="test")
        events = event_store.get_session_events("test")

        assert len(events) == 1
        _, retrieved = events[0]

        assert isinstance(retrieved, CircuitBreakerTripped)
        assert retrieved.component == "SessionGuard"
        assert retrieved.reason == "Max daily loss exceeded"
        assert retrieved.threshold == 10000.0
        assert retrieved.current_value == 10500.0

    def test_persistence_across_instances(self):
        """Test that events persist across EventStore instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_events.db"

            # Write events
            store1 = EventStore(db_path=db_path)
            store1.append(TickReceived(
                timestamp=datetime.now(timezone.utc),
                tick=Tick(
                    symbol="RELIANCE",
                    ltp=Decimal("2935.40"),
                    bid=Decimal("2935.35"),
                    ask=Decimal("2935.45"),
                    delta_volume=100,
                    cumulative_volume=1000,
                    exchange_timestamp=datetime.now(timezone.utc),
                )
            ), session_id="test")

            # Read events from new instance
            store2 = EventStore(db_path=db_path)
            events = store2.get_session_events("test")

            assert len(events) == 1
            assert isinstance(events[0][1], TickReceived)
            assert events[0][1].tick.symbol == "RELIANCE"

    def test_error_handling_invalid_event_type(self, event_store):
        """Test graceful handling of unknown event types."""
        # This should log warning but not crash
        events = event_store.get_session_events("nonexistent")
        assert events == []


class TestReplayEngineWithEvents:
    """Test ReplayEngine integration with EventStore."""

    @pytest.fixture
    def setup_replay(self):
        """Setup replay engine with event store."""

        executor = AsyncMock()
        executor.on_tick = AsyncMock()

        engine = ReplayEngine(executor=executor, speed_multiplier=1.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            event_store = EventStore(db_path=f"{tmpdir}/test_events.db")
            yield engine, event_store, executor

    def test_load_from_events(self, setup_replay):
        """Test loading ticks from event store."""
        engine, event_store, _ = setup_replay

        # Add tick events
        for i in range(10):
            event = TickReceived(
                timestamp=datetime.now(timezone.utc),
                tick=Tick(
                    symbol="RELIANCE",
                    ltp=Decimal("2935.40"),
                    bid=Decimal("2935.35"),
                    ask=Decimal("2935.45"),
                    delta_volume=100,
                    cumulative_volume=1000,
                    exchange_timestamp=datetime.now(timezone.utc),
                )
            )
            event_store.append(event, session_id="replay_test")

        # Load events into replay engine
        events = event_store.get_session_events("replay_test")
        tick_count = engine.load_from_events(events)

        assert tick_count == 10
        assert len(engine.ticks) == 10
        assert engine.cursor == 0

    def test_load_from_events_filters_non_ticks(self, setup_replay):
        """Test that only tick events are loaded."""
        engine, event_store, _ = setup_replay

        # Mix of tick and order events
        event_store.append(TickReceived(
            timestamp=datetime.now(timezone.utc),
            tick=Tick(
                symbol="RELIANCE",
                ltp=Decimal("2935.40"),
                bid=Decimal("2935.35"),
                ask=Decimal("2935.45"),
                delta_volume=100,
                cumulative_volume=1000,
                exchange_timestamp=datetime.now(timezone.utc),
            )
        ), session_id="test")

        event_store.append(OrderPlaced(
            timestamp=datetime.now(timezone.utc),
            order=Order(
                order_id="ord_1",
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100,
                price=Decimal("2935.00"),
                state=OrderState.OPEN,
            )
        ), session_id="test")

        events = event_store.get_session_events("test")
        tick_count = engine.load_from_events(events)

        # Only tick event loaded
        assert tick_count == 1
        assert len(engine.ticks) == 1

    @pytest.mark.asyncio
    async def test_replay_from_event_store(self, setup_replay):
        """Test full replay from event store."""
        engine, event_store, mock_executor = setup_replay

        # Add tick events
        for i in range(5):
            event = TickReceived(
                timestamp=datetime.now(timezone.utc),
                tick=Tick(
                    symbol="RELIANCE",
                    ltp=Decimal("2935.40"),
                    bid=Decimal("2935.35"),
                    ask=Decimal("2935.45"),
                    delta_volume=100,
                    cumulative_volume=1000,
                    exchange_timestamp=datetime.now(timezone.utc),
                )
            )
            event_store.append(event, session_id="replay_session")

        # Load and replay
        events = event_store.get_session_events("replay_session")
        engine.load_from_events(events)

        # Start replay
        await engine.start()

        # Verify all ticks were sent to executor
        assert mock_executor.on_tick.call_count == 5
        assert engine.cursor == 5
        assert not engine.is_running

    def test_checkpoint_save_restore(self, setup_replay):
        """Test checkpoint save and restore."""
        engine, _, _ = setup_replay

        # Load some ticks
        engine.ticks = [Mock() for _ in range(5)]
        engine.cursor = 3

        # Save checkpoint
        checkpoint = engine.save_checkpoint()
        assert checkpoint == 3

        # Move cursor
        engine.cursor = 0

        # Restore checkpoint
        engine.restore_checkpoint(checkpoint)
        assert engine.cursor == 3

    def test_checkpoint_restore_invalid_position(self, setup_replay):
        """Test that invalid checkpoint raises error."""
        engine, _, _ = setup_replay
        engine.ticks = [Mock() for _ in range(3)]

        with pytest.raises(ValueError, match="Invalid cursor"):
            engine.restore_checkpoint(100)
