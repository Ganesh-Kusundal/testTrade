from __future__ import annotations

import csv
import logging
import os
from typing import Any

from scalpr.adapters.dhan._auth import TokenManager
from scalpr.adapters.dhan._greeks import GreeksCalculator
from scalpr.adapters.dhan._historical import HistoricalDataAdapter
from scalpr.adapters.dhan._http import DhanHttpClient, RateLimiter
from scalpr.adapters.dhan._loader import InstrumentLoader
from scalpr.adapters.dhan._mapper import (
    conditional_trigger_to_dhan_request,
    forever_order_to_dhan_request,
    kill_switch_to_dhan,
    margin_calc_to_dhan_request,
    order_to_dhan_request_v2,
    response_to_fill,
    super_order_to_dhan_request,
    to_position,
    to_quote,
)
from scalpr.adapters.dhan._option_chain import OptionChainAdapter
from scalpr.adapters.dhan._portfolio import PortfolioAdapter
from scalpr.adapters.dhan._resolver import SymbolResolver
from scalpr.adapters.dhan._ws import DhanWebSocket
from scalpr.brokers.dhan.exceptions import DhanInstrumentNotFoundError as InstrumentNotFoundError
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

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self) -> None:
        try:
            csv_path = self._loader.ensure_loaded()
            self._csv_path = str(csv_path)
        except Exception as exc:
            logger.warning("instrument_download_failed; using configured csv_path: %s", exc)
        self._load_resolver()
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
        """Resolve symbol to (security_id, wire_segment).

        Falls back to the near-month futures contract for commodity
        underlyings (e.g. 'CRUDEOIL' on MCX -> CRUDEOIL-19Aug2026-FUT).
        """
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

    # ── Order execution ────────────────────────────────────────────────

    def _on_submit(self, msg: SubmitOrder) -> None:
        order = msg.order
        try:
            self._rate_limiter.acquire("orders")
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
            self._rate_limiter.acquire("orders")
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
            self._rate_limiter.acquire("orders")
            self._http_client.put(f"/orders/{msg.order_id}", data=msg.updates)
        except Exception as exc:
            logger.error("modify_failed: order_id=%s error=%s", msg.order_id, exc)

    # ── Public order API ───────────────────────────────────────────────

    def place_order(
        self,
        order: Order,
        product_type: str = "INTRADAY",
        after_market: bool = False,
        amo_time: str = "OPEN",
        bo_profit: float | None = None,
        bo_stop_loss: float | None = None,
        tag: str | None = None,
        should_slice: bool = False,
    ) -> str:
        self._rate_limiter.acquire("orders")
        self._token_manager.get_token()
        security_id, segment = self._resolve(order.symbol, order.exchange.value)
        req = order_to_dhan_request_v2(
            order, security_id, segment, self._client_id,
            product_type=product_type,
            after_market=after_market,
            amo_time=amo_time,
            bo_profit=bo_profit,
            bo_stop_loss=bo_stop_loss,
            disclosed_qty=0,
            tag=tag,
        )
        if should_slice:
            resp = self._http_client.post("/orders/slicing", data=req)
        else:
            resp = self._http_client.post("/orders", data=req)
        order_id: str = resp.get("orderId", "")
        return order_id

    def modify_order(self, order_id: str, **updates) -> bool:
        self._rate_limiter.acquire("orders")
        self._http_client.put(f"/orders/{order_id}", data=updates)
        return True

    def cancel_order(self, order_id: str) -> bool:
        self._rate_limiter.acquire("orders")
        self._http_client.delete(f"/orders/{order_id}")
        return True

    def get_order_detail(self, order_id: str) -> dict:
        self._rate_limiter.acquire("orders")
        return self._http_client.get(f"/orders/{order_id}", bucket="orders")

    def get_order_status(self, order_id: str) -> str:
        self._rate_limiter.acquire("orders")
        detail = self._http_client.get(f"/orders/{order_id}", bucket="orders")
        return detail.get("status", "")

    def get_executed_price(self, order_id: str) -> float:
        self._rate_limiter.acquire("orders")
        detail = self._http_client.get(f"/orders/{order_id}", bucket="orders")
        raw = detail.get("tradedPrice")
        if raw is None:
            return 0.0
        return float(raw)

    def get_executed_price_and_time(self, order_id: str) -> tuple[float, str]:
        self._rate_limiter.acquire("orders")
        detail = self._http_client.get(f"/orders/{order_id}", bucket="orders")
        raw = detail.get("tradedPrice")
        price = float(raw) if raw is not None else 0.0
        traded_at = detail.get("traded_at") or detail.get("tradedTime", "")
        return (price, traded_at)

    def cancel_all_orders(self, symbol: str | None = None) -> int:
        self._rate_limiter.acquire("orders")
        orders = self._http_client.get("/orders", bucket="orders")
        if isinstance(orders, dict):
            orders = orders.get("data", orders.get("orders", []))
        if not isinstance(orders, list):
            return 0
        open_statuses = {"OPEN", "PENDING", "TRIGGER PENDING", "PARTIALLY FILLED"}
        cancelled = 0
        for order in orders:
            status = order.get("status", "").upper()
            if status not in open_statuses:
                continue
            if symbol and order.get("tradingSymbol", order.get("symbol", "")) != symbol:
                continue
            try:
                self._http_client.delete(f"/orders/{order['orderId']}", bucket="orders")
                cancelled += 1
            except Exception:
                logger.exception("cancel_all_orders: failed for %s", order.get("orderId"))
        return cancelled

    def order_report(self, order_id: str) -> dict:
        self._rate_limiter.acquire("orders")
        return self._http_client.get(f"/orders/{order_id}", bucket="orders")

    def get_trade_book(self) -> list[dict]:
        self._rate_limiter.acquire("orders")
        data = self._http_client.get("/trades", bucket="orders")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("data", data.get("trades", []))
        return []

    def get_exchange_time(self) -> str:
        self._rate_limiter.acquire("orders")
        data = self._http_client.get("/exchange/time", bucket="orders")
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            return data.get("exchangeTime", data.get("time", data.get("dateTime", "")))
        return str(data)

    def kill_switch(self, action: str) -> str:
        self._rate_limiter.acquire("orders")
        req = kill_switch_to_dhan(action)
        resp = self._http_client.post("/killswitch", data=req)
        status: str = resp.get("killSwitchStatus", "")
        return status

    # ── Super orders ──────────────────────────────────────────────────

    def place_super_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        price: float,
        order_type: str = "LIMIT",
        product_type: str = "INTRADAY",
        target_price: float = 0.0,
        stop_loss_price: float = 0.0,
        trailing_jump: float = 0.0,
        tag: str | None = None,
    ) -> list[str]:
        self._rate_limiter.acquire("orders")
        self._token_manager.get_token()
        req = super_order_to_dhan_request(
            security_id, exchange_segment, transaction_type,
            quantity, order_type, product_type, price,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            trailing_jump=trailing_jump,
            tag=tag,
        )
        resp = self._http_client.post("/superorders", data=req)
        raw = resp.get("orderIds", resp.get("orderId", ""))
        if isinstance(raw, list):
            return raw
        return [raw] if raw else []

    def modify_super_order(
        self,
        order_id: str,
        quantity: int = 0,
        price: float = 0.0,
        order_type: str = "LIMIT",
        leg_name: str = "ENTRY_LEG",
        target_price: float = 0.0,
        stop_loss_price: float = 0.0,
        trailing_jump: float = 0.0,
    ) -> bool:
        self._rate_limiter.acquire("orders")
        payload: dict[str, Any] = {
            "orderId": order_id,
            "orderType": order_type.upper(),
            "legName": leg_name.upper(),
            "quantity": int(quantity),
            "price": float(price),
            "targetPrice": float(target_price),
            "stopLossPrice": float(stop_loss_price),
            "trailingJump": float(trailing_jump),
        }
        self._http_client.put(f"/superorders/{order_id}", data=payload)
        return True

    def cancel_super_order(self, order_id: str) -> bool:
        self._rate_limiter.acquire("orders")
        self._http_client.delete(f"/superorders/{order_id}")
        return True

    def get_super_orders(self) -> list[dict]:
        self._rate_limiter.acquire("orders")
        resp = self._http_client.get("/superorders", bucket="orders")
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict):
            return resp.get("data", resp.get("superOrders", []))
        return []

    # ── Forever / GTD orders ─────────────────────────────────────────

    def place_forever_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        price: float,
        trigger_price: float,
        order_type: str = "LIMIT",
        product_type: str = "INTRADAY",
        validity: str = "DAY",
        order_flag: str = "SINGLE",
        disclosed_quantity: int = 0,
        price1: float = 0.0,
        trigger_price1: float = 0.0,
        quantity1: int = 0,
        tag: str | None = None,
        symbol: str = "",
    ) -> str:
        self._rate_limiter.acquire("orders")
        self._token_manager.get_token()
        req = forever_order_to_dhan_request(
            security_id, exchange_segment, transaction_type,
            quantity, price, trigger_price, order_type, product_type,
            validity=validity, order_flag=order_flag,
            disclosed_quantity=disclosed_quantity,
            price1=price1, trigger_price1=trigger_price1,
            quantity1=quantity1, tag=tag, symbol=symbol,
        )
        resp = self._http_client.post("/foreverorders", data=req)
        order_id: str = resp.get("orderId", "")
        return order_id

    def modify_forever_order(
        self,
        order_id: str,
        quantity: int = 0,
        price: float = 0.0,
        order_type: str = "LIMIT",
        leg_name: str = "ENTRY_LEG",
        trigger_price: float = 0.0,
        disclosed_quantity: int = 0,
        validity: str = "DAY",
        order_flag: str = "SINGLE",
    ) -> bool:
        self._rate_limiter.acquire("orders")
        payload: dict[str, Any] = {
            "orderId": order_id,
            "orderFlag": order_flag.upper(),
            "orderType": order_type.upper(),
            "legName": leg_name.upper(),
            "quantity": int(quantity),
            "disclosedQuantity": int(disclosed_quantity),
            "price": float(price),
            "triggerPrice": float(trigger_price),
            "validity": validity.upper(),
        }
        self._http_client.put(f"/foreverorders/{order_id}", data=payload)
        return True

    def cancel_forever_order(self, order_id: str) -> bool:
        self._rate_limiter.acquire("orders")
        self._http_client.delete(f"/foreverorders/{order_id}")
        return True

    def get_forever_orders(self) -> list[dict]:
        self._rate_limiter.acquire("orders")
        resp = self._http_client.get("/foreverorders", bucket="orders")
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict):
            return resp.get("data", resp.get("foreverOrders", []))
        return []

    # ── Conditional triggers ─────────────────────────────────────────

    def place_conditional_trigger(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        price: float,
        trigger_price: float,
        order_type: str = "LIMIT",
        product_type: str = "INTRADAY",
        trigger_type: str = "PRICE_TRIGGER",
        validity: str = "DAY",
        disclosed_quantity: int = 0,
        tag: str | None = None,
    ) -> str:
        self._rate_limiter.acquire("orders")
        self._token_manager.get_token()
        req = conditional_trigger_to_dhan_request(
            security_id, exchange_segment, transaction_type,
            quantity, price, trigger_price, order_type, product_type,
            trigger_type=trigger_type, validity=validity,
            disclosed_quantity=disclosed_quantity, tag=tag,
        )
        resp = self._http_client.post("/triggers", data=req)
        trigger_id: str = resp.get("triggerId", "")
        return trigger_id

    def delete_conditional_trigger(self, trigger_id: str) -> bool:
        self._rate_limiter.acquire("orders")
        self._http_client.delete(f"/triggers/{trigger_id}")
        return True

    def get_all_conditional_triggers(self) -> list[dict]:
        self._rate_limiter.acquire("orders")
        resp = self._http_client.get("/triggers", bucket="orders")
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict):
            return resp.get("data", resp.get("triggers", []))
        return []

    def get_conditional_trigger_by_id(self, trigger_id: str) -> dict:
        self._rate_limiter.acquire("orders")
        resp = self._http_client.get(f"/triggers/{trigger_id}", bucket="orders")
        return resp if isinstance(resp, dict) else {}

    # ── Market data ────────────────────────────────────────────────────

    def subscribe_quotes(self, instrument_id: InstrumentId) -> None:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        self._ws.subscribe([(security_id, segment)], mode="quote")

    def unsubscribe_quotes(self, instrument_id: InstrumentId) -> None:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        self._ws.unsubscribe([(security_id, segment)])

    def get_quote(self, instrument_id: InstrumentId) -> dict[str, Any]:
        self._rate_limiter.acquire("market_data")
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        data = self._http_client.post(
            "/marketfeed/quote",
            data={"security_ids": [security_id], "exchangeSegment": segment},
            bucket="market_data",
        )
        return to_quote(data, instrument_id)

    def on_ws_tick(self, tick: QuoteTick) -> None:
        self._bus.publish("market.quote.dhan", tick)

    # ── Market depth ────────────────────────────────────────────────────

    def subscribe_market_depth(self, instrument_id: InstrumentId) -> None:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        self._ws.subscribe_depth([(security_id, segment)])

    def unsubscribe_market_depth(self, instrument_id: InstrumentId) -> None:
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        self._ws.unsubscribe_depth([(security_id, segment)])

    def get_market_depth_snapshot(self, instrument_id: InstrumentId) -> dict:
        self._rate_limiter.acquire("market_data")
        symbol, exchange = self._instrument_id_to_symbol_exchange(instrument_id)
        security_id, segment = self._resolve(symbol, exchange)
        data = self._http_client.post(
            "/marketfeed/depth",
            data={"security_ids": [security_id], "exchangeSegment": segment},
            bucket="market_data",
        )
        return data

    def get_market_depth_df(self, instrument_id: InstrumentId) -> list[dict]:
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
        return out

    # ── Portfolio ──────────────────────────────────────────────────────

    def get_positions(self) -> list[Position]:
        self._rate_limiter.acquire("portfolio")
        data = self._http_client.get("/positions", bucket="portfolio")
        if isinstance(data, list):
            return [to_position(item) for item in data]
        return [to_position(data)]

    def get_holdings(self) -> dict[str, Any]:
        self._rate_limiter.acquire("portfolio")
        return self._http_client.get("/holdings", bucket="portfolio")

    def get_funds(self) -> dict[str, Any]:
        self._rate_limiter.acquire("portfolio")
        return self._http_client.get("/fundlimit", bucket="portfolio")

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
        self._rate_limiter.acquire("portfolio")
        req = margin_calc_to_dhan_request(
            security_id, exchange_segment, transaction_type,
            quantity, product_type, price, trigger_price,
        )
        return self._http_client.post("/margincalculator", data=req, bucket="portfolio")

    def get_expired_option_data(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
        expiry_flag: str,
        expiry_code: int,
        strike: str,
        drv_option_type: str,
        required_data: list[str],
        from_date: str,
        to_date: str,
        interval: int = 1,
    ) -> dict[str, Any]:
        self._rate_limiter.acquire("history")
        payload = {
            "securityId": security_id,
            "exchangeSegment": exchange_segment,
            "instrument": instrument_type,
            "expiryFlag": expiry_flag,
            "expiryCode": expiry_code,
            "strike": strike,
            "drvOptionType": drv_option_type,
            "requiredData": required_data,
            "fromDate": from_date,
            "toDate": to_date,
            "interval": interval,
        }
        return self._http_client.post("/charts/rollingoption", data=payload, bucket="history")

    def get_live_pnl(self) -> float:
        return self._portfolio.get_live_pnl()

    def get_positions_summary(self) -> dict[str, Any]:
        return self._portfolio.get_positions_summary()

    # ── Historical data ────────────────────────────────────────────────

    def get_historical(
        self,
        symbol: str,
        exchange: str = "NSE",
        timeframe: str = "DAY",
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._historical.get_historical(symbol, exchange, timeframe, interval, from_date, to_date)

    def get_intraday(
        self,
        symbol: str,
        exchange: str = "NSE",
        interval: int = 5,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._historical.get_intraday(symbol, exchange, interval, from_date, to_date)

    def get_daily(
        self,
        symbol: str,
        exchange: str = "NSE",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._historical.get_daily(symbol, exchange, from_date, to_date)

    # ── Option chain ───────────────────────────────────────────────────

    def get_option_chain(
        self,
        symbol: str,
        exchange: str = "NSE",
        expiry: str | None = None,
    ) -> dict[str, Any]:
        return self._option_chain.get_option_chain(symbol, exchange, expiry=expiry)

    def get_expiry_list(self, symbol: str, exchange: str = "NSE") -> list[str]:
        return self._option_chain.get_expiry_list(symbol, exchange)

    def atm_strike(self, symbol: str, expiry_idx: int = 0, exchange: str = "NSE") -> tuple[str, str, float]:
        return self._option_chain.atm_strike_selection(symbol, expiry_idx=expiry_idx, exchange=exchange)

    def otm_strike(
        self, symbol: str, expiry_idx: int = 0, count: int = 1, exchange: str = "NSE",
    ) -> tuple[str, str, float, float]:
        return self._option_chain.otm_strike_selection(symbol, expiry_idx=expiry_idx, count=count, exchange=exchange)

    def itm_strike(
        self, symbol: str, expiry_idx: int = 0, count: int = 1, exchange: str = "NSE",
    ) -> tuple[str, str, float, float]:
        return self._option_chain.itm_strike_selection(symbol, expiry_idx=expiry_idx, count=count, exchange=exchange)

    def get_greeks(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        option_type: str,
        exchange: str = "NSE",
    ) -> dict | None:
        """Calculate options greeks for a contract using the local Black-Scholes model.

        Args:
            symbol: Underlying symbol (e.g. "NIFTY").
            expiry: Expiry date (ISO format, e.g. "2024-12-26").
            strike: Strike price.
            option_type: "CE" or "PE".
            exchange: Exchange (e.g. "NSE", "MCX").

        """
        return self._greeks.calculate_from_chain(symbol, expiry, strike, option_type, exchange=exchange)

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _instrument_id_to_symbol_exchange(instrument_id: InstrumentId) -> tuple[str, str]:
        if isinstance(instrument_id, SimpleInstrumentId):
            return instrument_id.symbol, instrument_id.exchange.value
        if isinstance(instrument_id, DerivativeInstrumentId):
            return instrument_id.underlying, instrument_id.exchange.value
        raise TypeError(f"Unsupported InstrumentId type: {type(instrument_id).__name__}")
