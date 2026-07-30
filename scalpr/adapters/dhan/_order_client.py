from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from scalpr.domain.order import Order

logger = logging.getLogger(__name__)


def _list_to_df(data: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(data)


class OrderClient:
    def __init__(
        self,
        http_provider,
        token_provider,
        client_id: str,
        resolve_fn,
    ) -> None:
        self._http_provider = http_provider
        self._token_provider = token_provider
        self._client_id = client_id
        self._resolve = resolve_fn

    @property
    def _http(self):
        return self._http_provider()

    @property
    def _token_manager(self):
        return self._token_provider()

    # ── Basic order CRUD ──────────────────────────────────────────────

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
        from scalpr.adapters.dhan.client import order_to_dhan_request_v2

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
            resp = self._http.post("/orders/slicing", data=req)
        else:
            resp = self._http.post("/orders", data=req)
        order_id: str = resp.get("orderId", "")
        return order_id

    def modify_order(self, order_id: str, **updates) -> bool:
        self._http.put(f"/orders/{order_id}", data=updates)
        return True

    def cancel_order(self, order_id: str) -> bool:
        self._http.delete(f"/orders/{order_id}")
        return True

    def get_order_detail(self, order_id: str, as_df: bool = False, debug: bool = False) -> dict | pd.DataFrame:
        if debug:
            logger.info("get_order_detail: order_id=%s", order_id)
        result = self._http.get(f"/orders/{order_id}", bucket="orders")
        if as_df:
            return pd.DataFrame([result])
        return result

    def get_order_status(self, order_id: str) -> str:
        detail = self._http.get(f"/orders/{order_id}", bucket="orders")
        return detail.get("status", "")

    def get_executed_price(self, order_id: str) -> float:
        detail = self._http.get(f"/orders/{order_id}", bucket="orders")
        raw = detail.get("tradedPrice")
        if raw is None:
            return 0.0
        return float(raw)

    def get_executed_price_and_time(self, order_id: str) -> tuple[float, str]:
        detail = self._http.get(f"/orders/{order_id}", bucket="orders")
        raw = detail.get("tradedPrice")
        price = float(raw) if raw is not None else 0.0
        traded_at = detail.get("traded_at") or detail.get("tradedTime", "")
        return (price, traded_at)

    def cancel_all_orders(self, symbol: str | None = None) -> int:
        orders = self._http.get("/orders", bucket="orders")
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
                self._http.delete(f"/orders/{order['orderId']}", bucket="orders")
                cancelled += 1
            except Exception:
                logger.exception("cancel_all_orders: failed for %s", order.get("orderId"))
        return cancelled

    def order_report(self, order_id: str, as_df: bool = False, debug: bool = False) -> dict | pd.DataFrame:
        if debug:
            logger.info("order_report: order_id=%s", order_id)
        result = self._http.get(f"/orders/{order_id}", bucket="orders")
        if as_df:
            return pd.DataFrame([result])
        return result

    def get_trade_book(self, as_df: bool = False, debug: bool = False) -> list[dict] | pd.DataFrame:
        if debug:
            logger.info("get_trade_book")
        data = self._http.get("/trades", bucket="orders")
        if isinstance(data, list):
            result = data
        elif isinstance(data, dict):
            result = data.get("data", data.get("trades", []))
        else:
            result = []
        if as_df:
            return _list_to_df(result)
        return result

    def kill_switch(self, action: str) -> str:
        from scalpr.adapters.dhan.client import kill_switch_to_dhan

        req = kill_switch_to_dhan(action)
        resp = self._http.post("/killswitch", data=req)
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
        from scalpr.adapters.dhan.client import super_order_to_dhan_request

        self._token_manager.get_token()
        req = super_order_to_dhan_request(
            security_id, exchange_segment, transaction_type,
            quantity, order_type, product_type, price,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            trailing_jump=trailing_jump,
            tag=tag,
        )
        resp = self._http.post("/superorders", data=req)
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
        self._http.put(f"/superorders/{order_id}", data=payload)
        return True

    def cancel_super_order(self, order_id: str) -> bool:
        self._http.delete(f"/superorders/{order_id}")
        return True

    def get_super_orders(self, as_df: bool = False) -> list[dict] | pd.DataFrame:
        resp = self._http.get("/superorders", bucket="orders")
        if isinstance(resp, list):
            result = resp
        elif isinstance(resp, dict):
            result = resp.get("data", resp.get("superOrders", []))
        else:
            result = []
        if as_df:
            return _list_to_df(result)
        return result

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
        from scalpr.adapters.dhan.client import forever_order_to_dhan_request

        self._token_manager.get_token()
        req = forever_order_to_dhan_request(
            security_id, exchange_segment, transaction_type,
            quantity, price, trigger_price, order_type, product_type,
            validity=validity, order_flag=order_flag,
            disclosed_quantity=disclosed_quantity,
            price1=price1, trigger_price1=trigger_price1,
            quantity1=quantity1, tag=tag, symbol=symbol,
        )
        resp = self._http.post("/foreverorders", data=req)
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
        self._http.put(f"/foreverorders/{order_id}", data=payload)
        return True

    def cancel_forever_order(self, order_id: str) -> bool:
        self._http.delete(f"/foreverorders/{order_id}")
        return True

    def get_forever_orders(self, as_df: bool = False) -> list[dict] | pd.DataFrame:
        resp = self._http.get("/foreverorders", bucket="orders")
        if isinstance(resp, list):
            result = resp
        elif isinstance(resp, dict):
            result = resp.get("data", resp.get("foreverOrders", []))
        else:
            result = []
        if as_df:
            return _list_to_df(result)
        return result

    # ── Conditional triggers ─────────────────────────────────────────

    def place_conditional_trigger(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        price: float,
        trigger_price: float = 0,
        order_type: str = "LIMIT",
        product_type: str = "INTRADAY",
        trigger_type: str = "PRICE_TRIGGER",
        validity: str = "DAY",
        disclosed_quantity: int = 0,
        tag: str | None = None,
        comparison_type: str = "PRICE_WITH_VALUE",
        operator: str | None = None,
        time_frame: str = "DAY",
        comparing_value: float | None = None,
        indicator_name: str | None = None,
        comparing_indicator_name: str | None = None,
        frequency: str = "ONCE",
        exp_date: str | None = None,
        user_note: str = "",
        timeout: int = 10,
    ) -> str:
        self._token_manager.get_token()
        payload: dict[str, Any] = {
            "triggerType": trigger_type.upper(),
            "exchangeSegment": exchange_segment.upper(),
            "securityId": security_id,
            "transactionType": transaction_type.upper(),
            "quantity": int(quantity),
            "disclosedQuantity": int(disclosed_quantity),
            "price": float(price),
            "triggerPrice": float(trigger_price),
            "orderType": order_type.upper(),
            "productType": product_type.upper(),
            "validity": validity.upper(),
            "comparisonType": comparison_type.upper(),
            "timeFrame": time_frame.upper(),
            "frequency": frequency.upper(),
            "userNote": user_note,
        }
        if tag:
            payload["correlationId"] = tag
        if operator:
            payload["operator"] = operator
        if comparing_value is not None:
            payload["comparingValue"] = float(comparing_value)
        if indicator_name:
            payload["indicatorName"] = indicator_name
        if comparing_indicator_name:
            payload["comparingIndicatorName"] = comparing_indicator_name
        if exp_date:
            payload["expDate"] = exp_date
        resp = self._http.post("/triggers", data=payload, bucket="orders")
        trigger_id: str = resp.get("triggerId", "")
        return trigger_id

    def delete_conditional_trigger(self, trigger_id: str) -> bool:
        self._http.delete(f"/triggers/{trigger_id}")
        return True

    def get_all_conditional_triggers(self, as_df: bool = False) -> list[dict] | pd.DataFrame:
        resp = self._http.get("/triggers", bucket="orders")
        if isinstance(resp, list):
            result = resp
        elif isinstance(resp, dict):
            result = resp.get("data", resp.get("triggers", []))
        else:
            result = []
        if as_df:
            return _list_to_df(result)
        return result

    def get_conditional_trigger_by_id(self, trigger_id: str, as_df: bool = False) -> dict | pd.DataFrame:
        resp = self._http.get(f"/triggers/{trigger_id}", bucket="orders")
        result = resp if isinstance(resp, dict) else {}
        if as_df:
            return pd.DataFrame([result])
        return result
