"""Persistent event store for event replay and audit trail.

Stores all domain events to SQLite for:
- Crash recovery and state reconstruction
- Replay of trading sessions (tick-by-tick)
- Audit trail and compliance
- Post-trade analysis
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from scalpr.domain.events import (
    BarClosed,
    CircuitBreakerTripped,
    DomainEvent,
    FillReceived,
    GateFailed,
    HistoricalDataLoaded,
    OrderCancelled,
    OrderExpired,
    OrderModified,
    OrderPlaced,
    OrderRejected,
    OrderUpdated,
    PositionClosed,
    PositionOpened,
    PositionReversed,
    PositionUpdated,
    RiskCheckFailed,
    RiskCheckPassed,
    SessionHalted,
    SignalGenerated,
    TickReceived,
)

logger = logging.getLogger(__name__)

# Event type registry for serialization/deserialization
EVENT_TYPE_REGISTRY: dict[str, type[DomainEvent]] = {
    "OrderPlaced": OrderPlaced,
    "OrderModified": OrderModified,
    "OrderCancelled": OrderCancelled,
    "OrderRejected": OrderRejected,
    "OrderExpired": OrderExpired,
    "OrderUpdated": OrderUpdated,
    "FillReceived": FillReceived,
    "PositionOpened": PositionOpened,
    "PositionClosed": PositionClosed,
    "PositionReversed": PositionReversed,
    "PositionUpdated": PositionUpdated,
    "TickReceived": TickReceived,
    "BarClosed": BarClosed,
    "HistoricalDataLoaded": HistoricalDataLoaded,
    "SignalGenerated": SignalGenerated,
    "GateFailed": GateFailed,
    "CircuitBreakerTripped": CircuitBreakerTripped,
    "RiskCheckPassed": RiskCheckPassed,
    "RiskCheckFailed": RiskCheckFailed,
    "SessionHalted": SessionHalted,
}


def _serialize_event(event: DomainEvent) -> dict[str, Any]:
    """Serialize domain event to JSON-compatible dict."""
    event_type = event.__class__.__name__
    data = {
        "event_type": event_type,
        "timestamp": event.timestamp.isoformat(),
    }

    # Extract event-specific fields
    for field_name in ("order", "fill", "position", "tick", "bar", "signal",
                       "reason", "error_code", "error_message", "component",
                       "gate_id", "gate_name", "check_name", "halted_by",
                       "symbol", "bar_count", "old_side", "new_side",
                       "old_price", "old_quantity", "previous_state",
                       "previous_quantity", "realized_pnl", "threshold",
                       "current_value"):
        if hasattr(event, field_name):
            value = getattr(event, field_name)
            if value is not None:
                # Handle complex objects
                if hasattr(value, "__dataclass_fields__"):  # dataclass
                    data[field_name] = _serialize_domain_object(value)
                elif isinstance(value, datetime):
                    data[field_name] = value.isoformat()
                else:
                    data[field_name] = value

    return data


def _serialize_domain_object(obj: Any) -> dict[str, Any]:
    """Serialize domain object (Order, Fill, Tick, etc.) to dict."""
    result = {}

    # For dataclasses, use __dataclass_fields__
    if hasattr(obj, "__dataclass_fields__"):
        for field_name in obj.__dataclass_fields__:
            try:
                value = getattr(obj, field_name)
                if callable(value):
                    continue
                # Convert to string if not primitive
                if hasattr(value, "name"):  # Enum
                    result[field_name] = value.name
                elif isinstance(value, datetime):
                    result[field_name] = value.isoformat()
                elif isinstance(value, Decimal):
                    result[field_name] = str(value)
                elif hasattr(value, "__dataclass_fields__"):  # Nested dataclass
                    result[field_name] = _serialize_domain_object(value)
                else:
                    result[field_name] = value
            except Exception:
                logger.debug("event_serialize_skip: field=%s", field_name, exc_info=True)
    else:
        # Fallback for non-dataclass objects
        for attr_name in dir(obj):
            if attr_name.startswith("_"):
                continue
            try:
                value = getattr(obj, attr_name)
                if callable(value):
                    continue
                # Convert to string if not primitive
                if hasattr(value, "name"):  # Enum
                    result[attr_name] = value.name
                elif isinstance(value, datetime):
                    result[attr_name] = value.isoformat()
                elif isinstance(value, Decimal):
                    result[attr_name] = str(value)
                else:
                    result[attr_name] = value
            except Exception:
                logger.debug("event_serialize_skip: attr=%s", attr_name, exc_info=True)

    return result


def _deserialize_event(data: dict[str, Any]) -> DomainEvent:
    """Deserialize JSON dict back to domain event."""
    event_type = data.pop("event_type")
    event_class = EVENT_TYPE_REGISTRY.get(event_type)

    if not event_class:
        raise ValueError(f"Unknown event type: {event_type}")

    # Convert timestamp back to datetime
    if "timestamp" in data:
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])

    # Reconstruct nested domain objects
    for field_name in ("tick", "order", "fill", "position", "bar", "signal"):
        if field_name in data and isinstance(data[field_name], dict):
            data[field_name] = _reconstruct_domain_object(field_name, data[field_name])

    try:
        return event_class(**data)
    except Exception as e:
        logger.error(f"Failed to deserialize event {event_type}: {e}")
        raise


def _reconstruct_domain_object(field_name: str, data: dict[str, Any]) -> Any:
    """Reconstruct domain object from dict."""
    from scalpr.domain.fill import Fill
    from scalpr.domain.instrument import Exchange
    from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
    from scalpr.domain.tick import Tick

    try:
        if field_name == "tick":
            return Tick(
                symbol=data.get("symbol", ""),
                ltp=Decimal(str(data.get("ltp", "0"))),
                bid=Decimal(str(data.get("bid", "0"))),
                ask=Decimal(str(data.get("ask", "0"))),
                delta_volume=data.get("delta_volume", 0),
                cumulative_volume=data.get("cumulative_volume", 0),
                exchange_timestamp=datetime.fromisoformat(data.get("exchange_timestamp", datetime.now(timezone.utc).isoformat())),
            )
        elif field_name == "order":
            return Order(
                order_id=data.get("order_id", ""),
                symbol=data.get("symbol", ""),
                exchange=Exchange[data.get("exchange", "NSE")],
                side=OrderSide[data.get("side", "BUY")],
                order_type=OrderType[data.get("order_type", "MARKET")],
                quantity=data.get("quantity", 0),
                price=Decimal(str(data.get("price", "0") or "0")),
                state=OrderState[data.get("state", "PENDING")],
            )
        elif field_name == "fill":
            return Fill(
                order_id=data.get("order_id", ""),
                fill_id=data.get("fill_id", ""),
                symbol=data.get("symbol", ""),
                side=OrderSide[data.get("side", "BUY")],
                quantity=data.get("quantity", 0),
                price=Decimal(str(data.get("price", "0"))),
                timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now(timezone.utc).isoformat())),
            )
        else:
            # For unsupported types, return dict (best effort)
            return data
    except Exception as e:
        logger.warning(f"Failed to reconstruct {field_name}: {e}")
        return data


class EventStore:
    """Persistent event store backed by SQLite.

    Provides:
    - Append-only event log for audit trail
    - Event stream retrieval for replay
    - Session-based event grouping
    - Fast event lookup by type/time
    """

    def __init__(self, db_path: str = "data/events.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()
        logger.info(f"EventStore initialized at {db_path}")

    def _init_db(self) -> None:
        """Initialize event store schema."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    sequence_num INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON events(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_seq ON events(session_id, sequence_num)"
            )

    def append(self, event: DomainEvent, session_id: str = "default") -> int:
        """Append event to store. Returns sequence number.

        Thread-safe. Appends atomically with auto-incrementing sequence.
        """
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            # Get next sequence number
            cursor = conn.execute(
                "SELECT COALESCE(MAX(sequence_num), 0) + 1 FROM events WHERE session_id = ?",
                (session_id,)
            )
            sequence_num = cursor.fetchone()[0]

            # Serialize and insert
            payload = json.dumps(_serialize_event(event))
            conn.execute(
                """INSERT INTO events (session_id, event_type, timestamp, sequence_num, payload)
                       VALUES (?, ?, ?, ?, ?)""",
                (
                    session_id,
                    event.__class__.__name__,
                    event.timestamp.isoformat(),
                    sequence_num,
                    payload,
                )
            )

            return sequence_num

    def get_session_events(
        self,
        session_id: str,
        from_seq: int = 0,
        to_seq: int | None = None,
        event_type: str | None = None,
    ) -> list[tuple[int, DomainEvent]]:
        """Get events for a session in sequence order.

        Args:
            session_id: Session identifier
            from_seq: Starting sequence number (inclusive)
            to_seq: Ending sequence number (inclusive), None for all
            event_type: Filter by event type (optional)

        Returns:
            List of (sequence_num, event) tuples
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            query = "SELECT sequence_num, payload FROM events WHERE session_id = ? AND sequence_num >= ?"
            params: list[Any] = [session_id, from_seq]

            if to_seq is not None:
                query += " AND sequence_num <= ?"
                params.append(to_seq)

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            query += " ORDER BY sequence_num ASC"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        # Deserialize events
        events = []
        for seq_num, payload_str in rows:
            try:
                payload = json.loads(payload_str)
                event = _deserialize_event(payload)
                events.append((seq_num, event))
            except Exception as e:
                logger.warning(f"Failed to deserialize event at seq {seq_num}: {e}")

        return events

    def get_latest_sequence(self, session_id: str) -> int:
        """Get the latest sequence number for a session."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT COALESCE(MAX(sequence_num), 0) FROM events WHERE session_id = ?",
                (session_id,)
            )
            return cursor.fetchone()[0]

    def get_event_count(self, session_id: str) -> int:
        """Get total event count for a session."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM events WHERE session_id = ?",
                (session_id,)
            )
            return cursor.fetchone()[0]

    def delete_session(self, session_id: str) -> int:
        """Delete all events for a session. Returns deleted count."""
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "DELETE FROM events WHERE session_id = ?",
                (session_id,)
            )
            count = cursor.rowcount
            logger.info(f"Deleted {count} events for session {session_id}")
            return count

    def compact(self, max_age_days: int = 30) -> int:
        """Compact old events. Returns deleted count.

        Args:
            max_age_days: Delete events older than this
        """
        with self._lock, sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "DELETE FROM events WHERE created_at < datetime('now', ?)",
                (f"-{max_age_days} days",)
            )
            count = cursor.rowcount
            if count > 0:
                logger.info(f"Compacted {count} events older than {max_age_days} days")
            return count
