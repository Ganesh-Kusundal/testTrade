from __future__ import annotations

import csv
import logging
import os
import threading
from decimal import Decimal
from typing import Any

import pandas as pd

from scalpr.adapters.dhan._auth import TokenManager
from scalpr.adapters.dhan._greeks import GreeksCalculator
from scalpr.adapters.dhan._historical import HistoricalDataAdapter
from scalpr.adapters.dhan._http import DhanHttpClient, RateLimiter
from scalpr.adapters.dhan._loader import InstrumentLoader
from scalpr.adapters.dhan._mapper_market import to_quote  # noqa: F401 — re-exported for test mocks
from scalpr.adapters.dhan._mapper_orders import (
    order_to_dhan_request_v2,
)
from scalpr.adapters.dhan._market_data_client import MarketDataClient
from scalpr.adapters.dhan._option_chain import OptionChainAdapter
from scalpr.adapters.dhan._order_client import OrderClient
from scalpr.adapters.dhan._order_registry import OrderRegistry
from scalpr.adapters.dhan._order_watcher import OrderWatcher
from scalpr.adapters.dhan._portfolio import PortfolioAdapter
from scalpr.adapters.dhan._resolver import DhanInstrumentNotFoundError as InstrumentNotFoundError
from scalpr.adapters.dhan._resolver import SymbolResolver
from scalpr.adapters.dhan._ws import DhanWebSocket
from scalpr.domain.contracts import MarketDepth, Quote
from scalpr.domain.instrument import (
    DerivativeInstrumentId,
    InstrumentId,
    ResolvedInstrument,
    SimpleInstrumentId,
)
from scalpr.domain.position import Position
from scalpr.domain.values import ZERO
from scalpr.engine.clock import Clock
from scalpr.engine.execution_engine import (
    CancelOrder,
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

logger = logging.getLogger(__name__)


class DhanClient:
    broker = "dhan"

    def __init__(self, bus: MessageBus, clock: Clock, config: dict) -> None:
        self._bus = bus
        self._clock = clock

        client_id: str = config["client_id"]
        access_token: str = config["access_token"]
        totp_secret: str = config["totp_secret"]
        csv_path: str = config.get("csv_path", "instrument.csv")

        self._client_id = client_id
        self._csv_path = csv_path

        pin: str = config.get("pin", "1111")
        self._token_manager = TokenManager(client_id, totp_secret, clock, pin=pin, initial_token=access_token)
        self._rate_limiter = RateLimiter()
        self._http_client = DhanHttpClient(
            client_id=client_id,
            access_token=access_token,
            token_manager=self._token_manager,
            rate_limiter=self._rate_limiter,
        )
        self._ws = DhanWebSocket(
            access_token=access_token,
            client_id=client_id,
            on_tick=self.on_ws_tick,
            clock=clock,
        )
        self._resolver = SymbolResolver()
        self._loader = InstrumentLoader()
        self._historical: HistoricalDataAdapter = HistoricalDataAdapter(self._http_client, self._resolver)
        self._option_chain: OptionChainAdapter = OptionChainAdapter(self._http_client, self._resolver)
        self._greeks: GreeksCalculator = GreeksCalculator(self._http_client, self._option_chain)
        self._portfolio: PortfolioAdapter = PortfolioAdapter(self._http_client)
        self._registry = OrderRegistry()
        self._order_watcher = OrderWatcher(
            http=self._http_client,
            bus=self._bus,
            clock=self._clock,
            registry=self._registry,
        )
        self._watcher_stop = threading.Event()
        self._watcher_thread: threading.Thread | None = None
        self._subscriptions: list[tuple[str, Any]] = []
        self._order_update_feed: Any = None

        def hp():
            return self._http_client
        def tp():
            return self._token_manager

        self._order_client = OrderClient(
            http_provider=hp,
            token_provider=tp,
            client_id=self._client_id,
            resolve_fn=self._resolve,
        )
        self._market_data_client = MarketDataClient(
            http_provider=hp,
            token_provider=tp,
            ws_provider=lambda: self._ws,
            historical_provider=lambda: self._historical,
            option_chain_provider=lambda: self._option_chain,
            greeks_provider=lambda: self._greeks,
            bus=self._bus,
            resolve_fn=self._resolve,
        )

    # ── Lifecycle ──────────────────────────────────────────────────────

    @property
    def registry(self) -> OrderRegistry:
        """Local order id <-> Dhan orderId map for this client."""
        return self._registry

    def start(self) -> None:
        try:
            csv_path = self._loader.ensure_loaded()
            self._csv_path = str(csv_path)
        except Exception as exc:
            logger.warning("instrument_download_failed; using configured csv_path: %s", exc)
        self._load_resolver()
        try:
            self._token_manager.get_token()
        except Exception as exc:
            logger.warning("token_fetch_at_startup_failed; API calls may fail: %s", exc)
        self._ws.connect()
        self._bus.subscribe("exec.command.submit.dhan", self._on_submit)
        self._bus.subscribe("exec.command.cancel.dhan", self._on_cancel)
        self._bus.subscribe("exec.command.modify.dhan", self._on_modify)
        self._subscriptions = [
            ("exec.command.submit.dhan", self._on_submit),
            ("exec.command.cancel.dhan", self._on_cancel),
            ("exec.command.modify.dhan", self._on_modify),
        ]
        self.start_order_watcher()

    def stop(self) -> None:
        self._stop_order_watcher()
        self._token_manager.stop()
        self._ws.disconnect()
        for topic, handler in self._subscriptions:
            self._bus.unsubscribe(topic, handler)
        self._subscriptions.clear()

    # ── Resolver load ──────────────────────────────────────────────────

    def _load_resolver(self) -> None:
        if not os.path.exists(self._csv_path):
            logger.warning("instrument_csv_not_found: %s", self._csv_path)
            return
        with open(self._csv_path, newline="") as f:
            reader = csv.DictReader(f)
            self._resolver.load_from_rows(reader)
        self._resolver.load_step_sizes(self._csv_path)
        logger.info("step_sizes_loaded: csv=%s", self._csv_path)

    # ─── Symbol resolution helper ──────────────────────────────────────

    def _resolve(self, symbol: str, exchange: str) -> tuple[str, str]:
        try:
            r = self._resolver.resolve_full(symbol, exchange)
            return r.security_id, r.wire_segment
        except InstrumentNotFoundError:
            if exchange == "MCX":
                futs = self._resolver.get_futures_for_underlying(symbol, exchange)
                if futs:
                    r = self._resolver.resolve_full(futs[0].symbol, exchange)
                    return r.security_id, r.wire_segment
            raise

    def resolve_instrument(self, identifier: str | SimpleInstrumentId) -> ResolvedInstrument:
        """Resolve a symbol string or InstrumentId to a ResolvedInstrument."""
        if isinstance(identifier, SimpleInstrumentId):
            symbol = identifier.symbol
            exchange = identifier.exchange.value
        elif isinstance(identifier, DerivativeInstrumentId):
            symbol = identifier.trading_symbol or identifier.underlying
            exchange = identifier.exchange.value
        else:
            parsed = SimpleInstrumentId.parse(str(identifier))
            symbol = parsed.symbol
            exchange = parsed.exchange.value
        return self._resolver.resolve_full(symbol, exchange)

    # ── Order-book watcher (fill ingress) ─────────────────────────────

    def start_order_watcher(self, interval_seconds: float = 5.0) -> None:
        """Start the order-book polling heartbeat. Idempotent."""
        if self._watcher_thread is not None and self._watcher_thread.is_alive():
            return
        self._watcher_stop.clear()
        self._watcher_interval = interval_seconds
        self._watcher_thread = threading.Thread(
            target=self._watcher_loop, name="dhan-order-watcher", daemon=True
        )
        self._watcher_thread.start()

    def poll_order_book(self) -> None:
        """Poll GET /orders once and publish any lifecycle changes."""
        self._order_watcher.poll_once()

    def _watcher_loop(self) -> None:
        while not self._watcher_stop.wait(self._watcher_interval):
            try:
                self._order_watcher.poll_once()
            except Exception as exc:
                logger.error("order_watch_loop_crashed: %s", exc)

    def _stop_order_watcher(self) -> None:
        self._watcher_stop.set()
        thread = self._watcher_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._watcher_thread = None

    # ── Bus handlers (stay on facade) ──────────────────────────────────

    def _on_submit(self, msg: SubmitOrder) -> None:
        order = msg.order
        try:
            self._token_manager.get_token()
            security_id, segment = self._resolve(order.symbol, order.exchange.value)
            req = order_to_dhan_request_v2(
                order, security_id, segment, self._client_id,
                product_type=order.product_type,
            )
            # The broker echoes correlationId back in the order book; carrying
            # the local order id here lets OrderWatcher re-attribute orders on
            # restart or after a lost submit response.
            req["correlationId"] = order.order_id
            resp = self._http_client.post("/orders", data=req)
            broker_order_id = str(resp.get("orderId") or "")
            if not broker_order_id:
                raise ValueError(f"broker response missing 'orderId': {resp!r}")
            self._registry.register(order.order_id, broker_order_id)
            self._bus.publish(
                "exec.event.accepted.dhan",
                OrderAccepted(
                    order_id=order.order_id,
                    timestamp=self._clock.timestamp(),
                    broker_order_id=broker_order_id,
                ),
            )
        except Exception as exc:
            logger.error("submit_failed: order_id=%s error=%s", order.order_id, exc)
            self._bus.publish(
                "exec.event.rejected.dhan",
                OrderRejected(
                    order_id=order.order_id,
                    reason=str(exc),
                    timestamp=self._clock.timestamp(),
                ),
            )

    def _on_cancel(self, msg: CancelOrder) -> None:
        broker_order_id = self._registry.broker_id(msg.order_id)
        if broker_order_id is None:
            logger.error("cancel_unmapped: order_id=%s", msg.order_id)
            self._bus.publish(
                "exec.event.cancel_rejected.dhan",
                OrderCancelRejected(
                    order_id=msg.order_id,
                    reason=f"unknown broker order id for {msg.order_id}",
                    timestamp=self._clock.timestamp(),
                ),
            )
            return
        try:
            self._http_client.delete(f"/orders/{broker_order_id}")
        except Exception as exc:
            logger.error("cancel_failed: order_id=%s error=%s", msg.order_id, exc)
            self._bus.publish(
                "exec.event.cancel_rejected.dhan",
                OrderCancelRejected(
                    order_id=msg.order_id,
                    reason=str(exc),
                    timestamp=self._clock.timestamp(),
                ),
            )
            return
        # Mark terminal FIRST: the watcher checks _terminal on every order-book
        # row, so this closes the window where a concurrent poll sees the
        # CANCELLED row and re-publishes a duplicate cancelled event. It also
        # drops the registry mapping before subscribers see the event.
        self._order_watcher.mark_terminal(broker_order_id, msg.order_id)
        self._bus.publish(
            "exec.event.cancelled.dhan",
            OrderCancelled(
                order_id=msg.order_id,
                timestamp=self._clock.timestamp(),
            ),
        )

    def _on_modify(self, msg: ModifyOrder) -> None:
        broker_order_id = self._registry.broker_id(msg.order_id)
        if broker_order_id is None:
            logger.error("modify_unmapped: order_id=%s", msg.order_id)
            self._bus.publish(
                "exec.event.modify_rejected.dhan",
                OrderModifyRejected(
                    order_id=msg.order_id,
                    reason=f"unknown broker order id for {msg.order_id}",
                    timestamp=self._clock.timestamp(),
                ),
            )
            return
        try:
            payload = self._build_modify_payload(broker_order_id, msg.updates)
            self._http_client.put(f"/orders/{broker_order_id}", data=payload)
        except Exception as exc:
            logger.error("modify_failed: order_id=%s error=%s", msg.order_id, exc)
            self._bus.publish(
                "exec.event.modify_rejected.dhan",
                OrderModifyRejected(
                    order_id=msg.order_id,
                    reason=str(exc),
                    timestamp=self._clock.timestamp(),
                ),
            )
            return
        self._bus.publish(
            "exec.event.modified.dhan",
            OrderModified(
                order_id=msg.order_id,
                updates=dict(msg.updates),
                timestamp=self._clock.timestamp(),
            ),
        )

    def _build_modify_payload(self, broker_order_id: str, updates: dict) -> dict:
        """Build a Dhan wire-format modify body from domain update keys.

        The engine's ModifyOrder.updates uses domain field names
        (price/quantity/trigger_price/validity); Dhan's PUT /orders/{id}
        expects orderType/legName/quantity/price/disclosedQuantity/
        triggerPrice/validity. The broker order book row supplies the fields
        that are not being changed.

        Fails closed: if the current order detail cannot be fetched, raise so
        the caller publishes modify_rejected. Guessing orderType (e.g.
        defaulting a STOP_LOSS order to LIMIT) would silently send a
        semantically different order to the broker.
        """
        try:
            detail = self._http_client.get(
                f"/orders/{broker_order_id}", bucket="orders"
            )
        except Exception as exc:
            raise ValueError(f"modify detail fetch failed: {exc}") from exc
        if isinstance(detail, list):
            detail = detail[0] if detail else {}
        if not isinstance(detail, dict) or not detail.get("orderType"):
            raise ValueError(f"modify detail unavailable for {broker_order_id}")

        payload = {
            "orderType": str(detail.get("orderType", "LIMIT")),
            "legName": str(detail.get("legName", "")),
            "quantity": int(updates.get("quantity", detail.get("quantity", 0))),
            "price": float(updates.get("price", detail.get("price", 0))),
            "disclosedQuantity": int(detail.get("disclosedQuantity", 0)),
            "triggerPrice": float(updates.get("trigger_price", detail.get("triggerPrice", 0))),
            "validity": str(updates.get("validity", detail.get("validity", "DAY"))),
        }
        return payload

    # ── High-level subscribe/unsubscribe API ────────────────────────────

    def subscribe(self, symbol: str, exchange: str = "NSE", type: str = "quote", level: int = 20) -> None:
        from scalpr.domain.instrument import Exchange
        exch = getattr(Exchange, exchange.upper(), Exchange.NSE)
        inst = SimpleInstrumentId(symbol, exch)
        if type == "quote":
            self.subscribe_quotes(inst)
        elif type == "depth":
            self.subscribe_market_depth(inst, level=level)
        else:
            raise ValueError(f"Unknown subscription type: {type!r}")

    def connect_order_updates(self) -> None:
        """Connect to the order-update WebSocket (Dhan provides a separate WS for order updates)."""
        from scalpr.adapters.dhan._order_update_ws import OrderUpdateFeed
        if self._order_update_feed is None:
            self._order_update_feed = OrderUpdateFeed(
                client_id=self._client_id,
                access_token=self._http_client.access_token,
                on_update=self._on_order_update_push,
            )
        self._order_update_feed.connect()

    def disconnect_order_updates(self) -> None:
        """Disconnect the order-update WebSocket."""
        if self._order_update_feed is not None:
            self._order_update_feed.disconnect()

    def _on_order_update_push(self, wire: dict) -> None:
        """Handle a push-based order update from the WS feed.

        Translates the wire dict into domain events and publishes to the bus,
        complementing the polling OrderWatcher path.
        """
        from scalpr.domain.order import OrderState, broker_status_to_order_state
        broker_order_id = str(wire.get("orderId", ""))
        local_id = self._registry.local_id(broker_order_id)
        status = wire.get("orderStatus", "")
        if not broker_order_id:
            return
        order_state = broker_status_to_order_state(status)
        if order_state == OrderState.FILLED:
            from scalpr.domain.fill import Fill
            from scalpr.domain.order import OrderSide
            fill_id = f"ws-{broker_order_id}-{int(self._clock.timestamp().timestamp())}"
            fill = Fill(
                fill_id=fill_id,
                order_id=local_id or broker_order_id,
                symbol=wire.get("tradingSymbol", ""),
                side=OrderSide.BUY if wire.get("transactionType") == "BUY" else OrderSide.SELL,
                quantity=int(wire.get("filledQty", 0)),
                price=Decimal(str(wire.get("avgPrice", 0))),
                timestamp=self._clock.timestamp(),
            )
            self._bus.publish(
                "exec.event.filled.dhan",
                OrderFilled(
                    order_id=local_id or broker_order_id,
                    fill=fill,
                    timestamp=self._clock.timestamp(),
                ),
            )
        elif order_state == OrderState.REJECTED:
            self._bus.publish(
                "exec.event.rejected.dhan",
                OrderRejected(
                    order_id=local_id or broker_order_id,
                    reason=wire.get("rejectReason", "rejected via WS"),
                    timestamp=self._clock.timestamp(),
                ),
            )
        elif order_state == OrderState.CANCELLED:
            self._bus.publish(
                "exec.event.cancelled.dhan",
                OrderCancelled(
                    order_id=local_id or broker_order_id,
                    timestamp=self._clock.timestamp(),
                ),
            )
        # Partial fills and terminal states for cancelled/rejected are already
        # handled above. Other statuses (PENDING, OPEN) are informational —
        # the OrderWatcher polls the order book for those.

    def unsubscribe(self, symbol: str, exchange: str = "NSE", type: str = "quote") -> None:
        from scalpr.domain.instrument import Exchange
        exch = getattr(Exchange, exchange.upper(), Exchange.NSE)
        inst = SimpleInstrumentId(symbol, exch)
        if type == "quote":
            self.unsubscribe_quotes(inst)
        elif type == "depth":
            self.unsubscribe_market_depth(inst)
        else:
            raise ValueError(f"Unknown subscription type: {type!r}")

    def subscribe_batch(self, specs: list[tuple[str, str, str, int | None]]) -> None:
        for symbol, exchange, feed_type, *rest in specs:
            level = rest[0] if rest and rest[0] is not None else 20
            self.subscribe(symbol, exchange, type=feed_type, level=level)

    def subscription_status(self) -> dict:
        return {
            "quote": {"count": self._ws.subscription_count, "capacity": self._ws.subscription_capacity_remaining},
            "depth_20": {"count": self._ws.depth_subscription_count_20, "capacity": self._ws.depth_capacity_remaining_20},
            "depth_200": {"count": self._ws.depth_subscription_count_200, "capacity": self._ws.depth_capacity_remaining_200},
        }

    # ── Delegated: OrderClient ─────────────────────────────────────────

    def place_order(self, *args, **kwargs) -> str:
        return self._order_client.place_order(*args, **kwargs)

    def modify_order(self, *args, **kwargs) -> bool:
        return self._order_client.modify_order(*args, **kwargs)

    def cancel_order(self, *args, **kwargs) -> bool:
        return self._order_client.cancel_order(*args, **kwargs)

    def get_order_detail(self, *args, **kwargs) -> dict | pd.DataFrame:
        return self._order_client.get_order_detail(*args, **kwargs)

    def get_order_status(self, *args, **kwargs) -> str:
        return self._order_client.get_order_status(*args, **kwargs)

    def get_executed_price(self, *args, **kwargs) -> float:
        return self._order_client.get_executed_price(*args, **kwargs)

    def get_executed_price_and_time(self, *args, **kwargs) -> tuple[float, str]:
        return self._order_client.get_executed_price_and_time(*args, **kwargs)

    def cancel_all_orders(self, *args, **kwargs) -> int:
        return self._order_client.cancel_all_orders(*args, **kwargs)

    def order_report(self, *args, **kwargs) -> dict | pd.DataFrame:
        return self._order_client.order_report(*args, **kwargs)

    def get_trade_book(self, *args, **kwargs) -> list[dict] | pd.DataFrame:
        return self._order_client.get_trade_book(*args, **kwargs)

    def kill_switch(self, *args, **kwargs) -> str:
        return self._order_client.kill_switch(*args, **kwargs)

    def status_kill_switch(self, *args, **kwargs) -> str:
        return self._order_client.status_kill_switch(*args, **kwargs)

    def place_super_order(self, *args, **kwargs) -> list[str]:
        return self._order_client.place_super_order(*args, **kwargs)

    def modify_super_order(self, *args, **kwargs) -> bool:
        return self._order_client.modify_super_order(*args, **kwargs)

    def cancel_super_order(self, *args, **kwargs) -> bool:
        return self._order_client.cancel_super_order(*args, **kwargs)

    def get_super_orders(self, *args, **kwargs) -> list[dict] | pd.DataFrame:
        return self._order_client.get_super_orders(*args, **kwargs)

    def place_forever_order(self, *args, **kwargs) -> str:
        return self._order_client.place_forever_order(*args, **kwargs)

    def modify_forever_order(self, *args, **kwargs) -> bool:
        return self._order_client.modify_forever_order(*args, **kwargs)

    def cancel_forever_order(self, *args, **kwargs) -> bool:
        return self._order_client.cancel_forever_order(*args, **kwargs)

    def get_forever_orders(self, *args, **kwargs) -> list[dict] | pd.DataFrame:
        return self._order_client.get_forever_orders(*args, **kwargs)

    def place_conditional_trigger(self, *args, **kwargs) -> str:
        return self._order_client.place_conditional_trigger(*args, **kwargs)

    def delete_conditional_trigger(self, *args, **kwargs) -> bool:
        return self._order_client.delete_conditional_trigger(*args, **kwargs)

    def get_all_conditional_triggers(self, *args, **kwargs) -> list[dict] | pd.DataFrame:
        return self._order_client.get_all_conditional_triggers(*args, **kwargs)

    def get_conditional_trigger_by_id(self, *args, **kwargs) -> dict | pd.DataFrame:
        return self._order_client.get_conditional_trigger_by_id(*args, **kwargs)

    # ── Delegated: MarketDataClient ────────────────────────────────────

    @property
    def ws_subscription_count(self):
        return self._ws.subscription_count

    @property
    def ws_depth_subscription_count(self):
        return self._ws.depth_subscription_count

    def subscribe_quotes(self, *args, **kwargs) -> None:
        return self._market_data_client.subscribe_quotes(*args, **kwargs)

    def unsubscribe_quotes(self, *args, **kwargs) -> None:
        return self._market_data_client.unsubscribe_quotes(*args, **kwargs)

    def get_quote(self, resolved: ResolvedInstrument | SimpleInstrumentId) -> Quote:
        """Return canonical Quote domain object."""
        if not isinstance(resolved, ResolvedInstrument):
            resolved = self.resolve_instrument(resolved)
        raw = self._market_data_client.get_quote(resolved.instrument_id)
        if isinstance(raw, dict):
            return _raw_to_domain_quote(raw, resolved)
        return raw

    def on_ws_tick(self, *args, **kwargs) -> None:
        return self._market_data_client.on_ws_tick(*args, **kwargs)

    def subscribe_market_depth(self, *args, **kwargs) -> None:
        return self._market_data_client.subscribe_market_depth(*args, **kwargs)

    def unsubscribe_market_depth(self, *args, **kwargs) -> None:
        return self._market_data_client.unsubscribe_market_depth(*args, **kwargs)

    def get_market_depth_snapshot(self, *args, **kwargs) -> dict:
        return self._market_data_client.get_market_depth_snapshot(*args, **kwargs)

    def get_market_depth_df(self, instrument_id: InstrumentId, as_df: bool = False) -> list[dict] | pd.DataFrame:
        return self._market_data_client._market_depth_df(
            self.get_market_depth_snapshot(instrument_id), as_df=as_df
        )

    def get_market_depth(self, instrument_id: InstrumentId) -> MarketDepth:
        """Return canonical MarketDepth domain model."""
        return self._market_data_client.get_market_depth(instrument_id)

    def get_historical_batch(self, *args, **kwargs) -> dict[str, pd.DataFrame | list[dict] | Exception]:
        return self._market_data_client.get_historical_batch(*args, **kwargs)

    def get_historical(self, *args, **kwargs) -> list[dict[str, Any]] | pd.DataFrame:
        return self._market_data_client.get_historical(*args, **kwargs)

    def get_intraday(self, *args, **kwargs) -> list[dict[str, Any]] | pd.DataFrame:
        return self._market_data_client.get_intraday(*args, **kwargs)

    def get_daily(self, *args, **kwargs) -> list[dict[str, Any]] | pd.DataFrame:
        return self._market_data_client.get_daily(*args, **kwargs)

    def get_option_chain(self, *args, **kwargs) -> dict[str, Any] | pd.DataFrame:
        return self._market_data_client.get_option_chain(*args, **kwargs)

    def get_expiry_list(self, *args, **kwargs) -> list[str] | pd.Series:
        return self._market_data_client.get_expiry_list(*args, **kwargs)

    def atm_strike(self, *args, **kwargs) -> tuple[str, str, float]:
        return self._market_data_client.atm_strike(*args, **kwargs)

    def otm_strike(self, *args, **kwargs) -> tuple[str, str, float, float]:
        return self._market_data_client.otm_strike(*args, **kwargs)

    def itm_strike(self, *args, **kwargs) -> tuple[str, str, float, float]:
        return self._market_data_client.itm_strike(*args, **kwargs)

    def get_greeks(self, *args, **kwargs) -> dict | pd.DataFrame | None:
        return self._market_data_client.get_greeks(*args, **kwargs)

    @staticmethod
    def resample_timeframe(*args, **kwargs) -> pd.DataFrame:
        return MarketDataClient.resample_timeframe(*args, **kwargs)

    @staticmethod
    def renko_bricks(*args, **kwargs) -> pd.DataFrame:
        return MarketDataClient.renko_bricks(*args, **kwargs)

    @staticmethod
    def heikin_ashi(*args, **kwargs) -> pd.DataFrame:
        return MarketDataClient.heikin_ashi(*args, **kwargs)

    # ── Portfolio (delegated to PortfolioAdapter) ──────────────────────

    def get_positions(self, as_df: bool = False, debug: bool = False) -> list[Position] | pd.DataFrame:
        return self._portfolio.get_positions(as_df=as_df, debug=debug)

    def get_holdings(self, as_df: bool = False, debug: bool = False) -> dict[str, Any] | pd.DataFrame:
        return self._portfolio.get_holdings(as_df=as_df, debug=debug)

    def get_funds(self, as_df: bool = False, debug: bool = False) -> dict[str, Any] | pd.DataFrame:
        return self._portfolio.get_funds(as_df=as_df, debug=debug)

    def margin_calculator(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        product_type: str,
        price: float,
        trigger_price: float = 0,
    ) -> dict[str, Any]:
        return self._portfolio.margin_calculator(
            security_id, exchange_segment, transaction_type,
            quantity, product_type, price, trigger_price,
        )

    def get_expired_option_data(
        self,
        security_id: str,
        exchange_segment: str = "NSE_FNO",
        instrument_type: str = "OPT",
        expiry_flag: str = "MONTH",
        expiry_code: int = 1,
        strike: str = "ATM",
        drv_option_type: str = "CE",
        required_data: list[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        interval: int = 1,
    ) -> dict[str, Any]:
        return self._portfolio.get_expired_option_data(
            security_id, exchange_segment, instrument_type,
            expiry_flag, expiry_code, strike, drv_option_type,
            required_data, from_date, to_date, interval,
        )

    def get_live_pnl(self) -> float:
        return self._portfolio.get_live_pnl()

    def get_positions_summary(self) -> dict[str, Any]:
        return self._portfolio.get_positions_summary()

    def get_lot_size(self, symbol: str, exchange: str = "NSE") -> int:
        """Get lot size for a symbol from the resolver."""
        try:
            r = self._resolver.resolve_full(symbol, exchange)
            return r.lot_size if hasattr(r, "lot_size") else 1
        except Exception:
            return 1

    def get_expiry_date(self, symbol: str, exchange: str = "NSE", instrument: str = "OPT") -> list[str]:
        """Get sorted expiry dates for a symbol from the resolver."""
        try:
            return self._resolver.get_expiry_dates(symbol, exchange, instrument)
        except Exception:
            return []

    def convert_epoch_to_ist(self, epoch: int | float) -> str:
        """Convert Dhan epoch timestamp to IST datetime string."""
        from datetime import datetime, timedelta, timezone
        ist = timezone(timedelta(hours=5, minutes=30))
        return datetime.fromtimestamp(epoch, tz=ist).strftime("%Y-%m-%d %H:%M:%S")

    def get_exchange_time(self) -> str:
        return self._portfolio.get_exchange_time()


def _raw_to_domain_quote(raw: dict[str, Any], resolved: ResolvedInstrument) -> Quote:
    """Convert a raw Dhan quote dict to the canonical domain Quote."""
    from datetime import datetime, timezone
    from decimal import Decimal

    ohlc = raw.get("ohlc", {})
    ltp = Decimal(str(raw.get("last_price", raw.get("ltp", 0))))
    net_change = Decimal(str(raw.get("net_change", 0)))
    close = Decimal(str(ohlc.get("close", raw.get("close", 0))))
    change_percent = (net_change / close * 100) if close else ZERO

    ts = raw.get("timestamp")
    if isinstance(ts, (int, float)):
        timestamp = datetime.fromtimestamp(float(ts), tz=timezone.utc)
    elif isinstance(ts, datetime):
        timestamp = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    else:
        timestamp = None

    return Quote(
        symbol=resolved.trading_symbol,
        exchange=resolved.exchange.value,
        ltp=ltp,
        open=Decimal(str(ohlc.get("open", 0))),
        high=Decimal(str(ohlc.get("high", 0))),
        low=Decimal(str(ohlc.get("low", 0))),
        close=close,
        volume=int(raw.get("volume", 0)),
        change=net_change,
        change_percent=change_percent,
        timestamp=timestamp,
        oi=int(raw.get("oi", 0)),
    )
