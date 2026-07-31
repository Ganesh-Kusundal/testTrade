"""Order-update WebSocket — push-based fill/reject/cancel path.

Runs the dhanhq ``OrderUpdate`` feed in a daemon thread.  The SDK's own
``handle_order_update`` is overridden so that every incoming order-alert is
normalised into a wire-format dict and published to the message bus on
``exec.event.order_update.dhan``.

This is the *push* complement to the *polling* ``OrderWatcher``.
Both feed into the same bus topic; the engine deduplicates by broker order id
and status.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class OrderUpdateFeed:
    """Thin wrapper around dhanhq.OrderUpdate that runs in a daemon thread."""

    def __init__(
        self,
        client_id: str,
        access_token: str,
        on_update: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._client_id = client_id
        self._access_token = access_token
        self._on_update = on_update
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._feed: Any = None

    # -- lifecycle -----------------------------------------------------------

    def connect(self) -> None:
        """Start the order-update WS in a daemon thread.  Idempotent."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="dhan-order-update-ws", daemon=True,
        )
        self._thread.start()

    def disconnect(self) -> None:
        """Signal the thread to stop and wait briefly."""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=3.0)
        self._thread = None

    @property
    def connected(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- internals -----------------------------------------------------------

    def _run(self) -> None:
        try:
            self._run_async()
        except Exception as exc:
            if not self._stop.is_set():
                logger.error("order_update_ws_crashed: %s", exc)

    def _run_async(self) -> None:
        from dhanhq import DhanContext, OrderUpdate

        ctx = DhanContext(self._client_id, self._access_token)

        class _Feed(OrderUpdate):
            """Subclass that intercepts handle_order_update."""

            def __init__(s, dhan_ctx: Any) -> None:  # noqa: N805
                super().__init__(dhan_ctx)
                s._oup_on_update = self._on_update
                s._oup_stop = self._stop

            async def handle_order_update(s, order_update: dict) -> None:  # noqa: N805
                if s._oup_stop.is_set():
                    return
                try:
                    await self._handle_update(order_update)
                except Exception as exc:
                    logger.warning("order_update_handle_error: %s", exc)

        self._feed = _Feed(ctx)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._feed.connect_order_update())
        except Exception as exc:
            if not self._stop.is_set():
                logger.error("order_update_ws_error: %s", exc)
        finally:
            loop.close()

    async def _handle_update(self, raw: dict[str, Any]) -> None:
        """Parse a raw order-alert dict and publish to the bus."""
        msg_type = raw.get("Type", "")
        if msg_type != "order_alert":
            return
        data = raw.get("Data", {})
        if not data:
            return

        wire = self._normalise(data)
        if wire and self._on_update is not None:
            try:
                self._on_update(wire)
            except Exception as exc:
                logger.warning("order_update_cb_error: %s", exc)

    @staticmethod
    def _normalise(data: dict[str, Any]) -> dict[str, Any]:
        """Translate SDK wire dict into the canonical shape used by the bus.

        Dhan SDK fields (order_alert.Data):
            orderNo, status, filledQty, remainingQty, avgPrice,
            orderTimestamp, rejectReason, tradingSymbol, ...
        Bus wire shape:
            orderId, orderStatus, filledQty, remainingQty, avgPrice,
            timestamp, rejectReason, ...
        """
        return {
            "orderId": str(data.get("orderNo", "")),
            "orderStatus": str(data.get("status", "")),
            "filledQty": int(data.get("filledQty", 0)),
            "remainingQty": int(data.get("remainingQty", 0)),
            "avgPrice": float(data.get("avgPrice", 0)),
            "timestamp": data.get("orderTimestamp"),
            "rejectReason": data.get("rejectReason"),
            "tradingSymbol": data.get("tradingSymbol"),
            "transactionType": data.get("transactionType"),
            "orderType": data.get("orderType"),
            "productType": data.get("productType"),
            "quantity": int(data.get("quantity", 0)),
            "price": float(data.get("price", 0)),
            "triggerPrice": float(data.get("triggerPrice", 0)),
            "correlationId": data.get("correlationId"),
        }
