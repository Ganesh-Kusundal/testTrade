"""Order-book polling watcher — the adapter's fill ingress.

Dhan's POST /orders response only tells us the order was accepted. Execution
arrives later. This watcher polls GET /orders on a heartbeat, diffs each row
against what it last saw, and publishes the delta as domain events.

Deltas, not totals: the order book reports cumulative filled quantity, so
publishing it raw on every poll would count the same lots repeatedly and
inflate the position.

Field names are the real Dhan order-book names: ``filledQty``,
``averageTradedPrice``, ``orderStatus``.
"""

from __future__ import annotations

import dataclasses
import logging
import threading
from typing import Any

from scalpr.adapters.dhan._mapper_orders import (
    order_book_entry_to_fill,
    order_status_from_dhan,
)
from scalpr.adapters.dhan._order_registry import OrderRegistry
from scalpr.domain.order import OrderState
from scalpr.engine.clock import Clock
from scalpr.engine.execution_engine import (
    OrderCancelled,
    OrderFilled,
    OrderRejected,
)
from scalpr.engine.message_bus import MessageBus

logger = logging.getLogger(__name__)


class OrderWatcher:
    """Polls the Dhan order book and publishes lifecycle events for deltas."""

    def __init__(
        self,
        http: Any,
        bus: MessageBus,
        clock: Clock,
        registry: OrderRegistry,
    ) -> None:
        self._http = http
        self._bus = bus
        self._clock = clock
        self._registry = registry
        self._seen_filled: dict[str, int] = {}
        self._terminal: set[str] = set()
        # _seen_filled / _terminal are touched both by the polling thread and
        # by client._on_cancel (via mark_terminal) on the bus thread.
        self._lock = threading.Lock()

    def poll_once(self) -> None:
        """Fetch the order book and publish whatever changed. Never raises."""
        try:
            book = self._http.get("/orders", bucket="orders")
        except Exception as exc:
            logger.warning("order_book_poll_failed: %s", exc)
            return
        if isinstance(book, dict):
            # Defensive: some environments wrap the list under a key.
            book = book.get("data") or book.get("orders") or []
        if not isinstance(book, list):
            logger.warning("order_book_unexpected_shape: %r", type(book))
            return
        seen: set[str] = set()
        for entry in book:
            try:
                self._process(entry)
            except Exception as exc:
                logger.warning(
                    "order_book_entry_skipped: orderId=%s error=%s",
                    entry.get("orderId") if isinstance(entry, dict) else "?",
                    exc,
                )
            if isinstance(entry, dict) and entry.get("orderId"):
                seen.add(str(entry["orderId"]))
        # The order book only carries today's rows. Drop tracking state for
        # ids that have left it, so a long-running session does not accumulate
        # a terminal set and delta baseline forever.
        with self._lock:
            for stale in list(self._terminal - seen):
                self._terminal.discard(stale)
            for stale in list(self._seen_filled.keys() - seen):
                self._seen_filled.pop(stale, None)

    def _process(self, entry: dict) -> None:
        broker_order_id = str(entry.get("orderId") or "")
        if not broker_order_id:
            return
        with self._lock:
            terminal = broker_order_id in self._terminal
        if terminal:
            return
        local_order_id = self._registry.local_id(broker_order_id)
        if local_order_id is None:
            # Recovery for a submit whose response was lost, or a process
            # restart: the local order id is sent to the broker as
            # correlationId, so a previously-unregistered row can still be
            # attributed to us.
            correlation = entry.get("correlationId")
            if correlation:
                self._registry.register(str(correlation), broker_order_id)
                local_order_id = str(correlation)
            else:
                # Placed outside this process — not ours to report on.
                return

        try:
            state = order_status_from_dhan(str(entry.get("orderStatus", "")))
        except Exception as exc:
            logger.warning("order_status_unmapped: %s", exc)
            return

        self._emit_fill_delta(entry, broker_order_id, local_order_id)
        self._emit_terminal(state, broker_order_id, local_order_id)

    def _emit_fill_delta(
        self, entry: dict, broker_order_id: str, local_order_id: str
    ) -> None:
        raw_filled = entry.get("filledQty", entry.get("filledQuantity", 0))
        try:
            filled = int(raw_filled)
        except (TypeError, ValueError):
            return
        with self._lock:
            previous = self._seen_filled.get(broker_order_id, 0)
            delta = filled - previous
        if delta <= 0:
            return
        try:
            fill = order_book_entry_to_fill(entry, local_order_id, delta)
            fill = dataclasses.replace(fill, timestamp=self._clock.utc_now())
        except Exception as exc:
            logger.warning("order_book_fill_unmappable: orderId=%s error=%s", broker_order_id, exc)
            return
        # Record first, publish last (at-most-once): if a subscriber raises
        # mid-publish, _seen_filled has already advanced, so the next poll will
        # NOT recompute the same delta and re-publish it — a duplicate fill
        # would double-count the position, which is worse than a lost one.
        with self._lock:
            self._seen_filled[broker_order_id] = filled
        self._bus.publish(
            "exec.event.filled.dhan",
            OrderFilled(
                order_id=local_order_id,
                fill=fill,
                timestamp=self._clock.timestamp(),
            ),
        )

    def _emit_terminal(
        self, state: OrderState, broker_order_id: str, local_order_id: str
    ) -> None:
        # Re-check under the lock: a concurrent client._on_cancel may have
        # marked this order terminal between our _process check and now.
        # Without this an in-flight poll can double-publish a cancel that the
        # client already confirmed optimistically.
        with self._lock:
            if broker_order_id in self._terminal:
                return
        if state == OrderState.REJECTED:
            self._bus.publish(
                "exec.event.rejected.dhan",
                OrderRejected(
                    order_id=local_order_id,
                    reason="rejected by broker",
                    timestamp=self._clock.timestamp(),
                ),
            )
            self._finalize(broker_order_id, local_order_id)
        elif state in (OrderState.CANCELLED, OrderState.EXPIRED):
            self._bus.publish(
                "exec.event.cancelled.dhan",
                OrderCancelled(
                    order_id=local_order_id,
                    timestamp=self._clock.timestamp(),
                ),
            )
            self._finalize(broker_order_id, local_order_id)
        elif state == OrderState.FILLED:
            # The fill delta already carried the quantity; just stop watching.
            self._finalize(broker_order_id, local_order_id)

    def _finalize(self, broker_order_id: str, local_order_id: str) -> None:
        """Stop tracking a terminal order so memory stays bounded."""
        with self._lock:
            self._terminal.add(broker_order_id)
            self._seen_filled.pop(broker_order_id, None)
        self._registry.forget(local_order_id)

    def mark_terminal(self, broker_order_id: str, local_order_id: str) -> None:
        """Tell the watcher an order already reached a terminal state.

        Used when the client confirms a cancel optimistically (DELETE 200):
        without this the watcher would re-publish exec.event.cancelled.dhan
        when it later sees the CANCELLED row in the order book, duplicating
        the event for every subscriber.
        """
        self._finalize(broker_order_id, local_order_id)
