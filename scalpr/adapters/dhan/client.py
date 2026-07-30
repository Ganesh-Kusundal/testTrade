from __future__ import annotations

import csv
import logging
import os
from typing import Any

import pandas as pd

from scalpr.adapters.dhan._auth import TokenManager
from scalpr.adapters.dhan._greeks import GreeksCalculator
from scalpr.adapters.dhan._historical import HistoricalDataAdapter
from scalpr.adapters.dhan._http import DhanHttpClient, RateLimiter
from scalpr.adapters.dhan._loader import InstrumentLoader
from scalpr.adapters.dhan._mapper import (  # noqa: F401 — imported for test patch targets
    forever_order_to_dhan_request,
    kill_switch_to_dhan,
    margin_calc_to_dhan_request,
    order_to_dhan_request_v2,
    response_to_fill,
    super_order_to_dhan_request,
    to_position,
    to_quote,
)
from scalpr.adapters.dhan._market_data_client import MarketDataClient
from scalpr.adapters.dhan._option_chain import OptionChainAdapter
from scalpr.adapters.dhan._order_client import OrderClient
from scalpr.adapters.dhan._portfolio import PortfolioAdapter
from scalpr.adapters.dhan._portfolio_client import PortfolioClient
from scalpr.adapters.dhan._resolver import SymbolResolver
from scalpr.adapters.dhan._resolver import DhanInstrumentNotFoundError as InstrumentNotFoundError
from scalpr.adapters.dhan._ws import DhanWebSocket
from scalpr.domain.instrument import (
    DerivativeInstrumentId,
    InstrumentId,
    SimpleInstrumentId,
)
from scalpr.domain.order import Order
from scalpr.domain.position import Position
from scalpr.domain.tick import Tick as QuoteTick
from scalpr.engine.clock import Clock
from scalpr.engine.execution_engine import (
    CancelOrder,
    ModifyOrder,
    OrderCancelled,
    OrderFilled,
    OrderRejected,
    SubmitOrder,
)
from scalpr.engine.message_bus import MessageBus

logger = logging.getLogger(__name__)


class DhanClient:
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
        self._subscriptions: list[tuple[str, Any]] = []

        hp = lambda: self._http_client
        tp = lambda: self._token_manager

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
        self._portfolio_client = PortfolioClient(
            http_provider=hp,
            token_provider=tp,
            portfolio=self._portfolio,
        )

    # ── Lifecycle ──────────────────────────────────────────────────────

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

    def stop(self) -> None:
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
            resp = self._http_client.post("/orders", data=req)
            fill = response_to_fill(resp, order)
            self._bus.publish(
                "exec.event.filled.dhan",
                OrderFilled(
                    order_id=order.order_id,
                    fill=fill,
                    timestamp=self._clock.timestamp(),
                ),
            )
        except Exception as exc:
            logger.error("submit_failed: %s", exc)
            self._bus.publish(
                "exec.event.rejected.dhan",
                OrderRejected(
                    order_id=order.order_id,
                    reason=str(exc),
                    timestamp=self._clock.timestamp(),
                ),
            )

    def _on_cancel(self, msg: CancelOrder) -> None:
        try:
            self._http_client.delete(f"/orders/{msg.order_id}")
            self._bus.publish(
                "exec.event.cancelled.dhan",
                OrderCancelled(
                    order_id=msg.order_id,
                    timestamp=self._clock.timestamp(),
                ),
            )
        except Exception as exc:
            logger.error("cancel_failed: order_id=%s error=%s", msg.order_id, exc)

    def _on_modify(self, msg: ModifyOrder) -> None:
        try:
            self._http_client.put(f"/orders/{msg.order_id}", data=msg.updates)
        except Exception as exc:
            logger.error("modify_failed: order_id=%s error=%s", msg.order_id, exc)

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

    def get_quote(self, *args, **kwargs) -> dict[str, Any]:
        return self._market_data_client.get_quote(*args, **kwargs)

    def on_ws_tick(self, *args, **kwargs) -> None:
        return self._market_data_client.on_ws_tick(*args, **kwargs)

    def subscribe_market_depth(self, *args, **kwargs) -> None:
        return self._market_data_client.subscribe_market_depth(*args, **kwargs)

    def unsubscribe_market_depth(self, *args, **kwargs) -> None:
        return self._market_data_client.unsubscribe_market_depth(*args, **kwargs)

    def get_market_depth_snapshot(self, *args, **kwargs) -> dict:
        return self._market_data_client.get_market_depth_snapshot(*args, **kwargs)

    def get_market_depth_df(self, instrument_id: InstrumentId, as_df: bool = False) -> list[dict] | pd.DataFrame:
        raw = self.get_market_depth_snapshot(instrument_id)
        depth = raw.get("depth") or {}
        bids = depth.get("bid") or []
        asks = depth.get("ask") or []

        bid_sorted = sorted(bids, key=lambda x: float(x.get("price", 0)), reverse=True)
        ask_sorted = sorted(asks, key=lambda x: float(x.get("price", 0)))

        out: list[dict] = []
        min_len = min(len(bid_sorted), len(ask_sorted))
        for i in range(min_len):
            b = bid_sorted[i]
            a = ask_sorted[i]
            out.append({
                "level": i + 1,
                "bid_price": float(b.get("price", 0)),
                "bid_qty": int(b.get("quantity", 0)),
                "bid_orders": int(b.get("orders", 0)),
                "ask_price": float(a.get("price", 0)),
                "ask_qty": int(a.get("quantity", 0)),
                "ask_orders": int(a.get("orders", 0)),
            })
        if as_df:
            return pd.DataFrame(out)
        return out

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

    # ── Delegated: PortfolioClient ─────────────────────────────────────

    def get_positions(self, *args, **kwargs) -> list[Position] | pd.DataFrame:
        return self._portfolio_client.get_positions(*args, **kwargs)

    def get_holdings(self, *args, **kwargs) -> dict[str, Any] | pd.DataFrame:
        return self._portfolio_client.get_holdings(*args, **kwargs)

    def get_funds(self, *args, **kwargs) -> dict[str, Any] | pd.DataFrame:
        return self._portfolio_client.get_funds(*args, **kwargs)

    def margin_calculator(self, *args, **kwargs) -> dict[str, Any]:
        return self._portfolio_client.margin_calculator(*args, **kwargs)

    def get_expired_option_data(self, *args, **kwargs) -> dict[str, Any]:
        return self._portfolio_client.get_expired_option_data(*args, **kwargs)

    def get_live_pnl(self, *args, **kwargs) -> float:
        return self._portfolio_client.get_live_pnl(*args, **kwargs)

    def get_positions_summary(self, *args, **kwargs) -> dict[str, Any]:
        return self._portfolio_client.get_positions_summary(*args, **kwargs)

    def get_exchange_time(self, *args, **kwargs) -> str:
        return self._portfolio_client.get_exchange_time(*args, **kwargs)
