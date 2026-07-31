from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import (
    BROKER_STATUS_TO_ORDER_STATE,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)


class MappingError(Exception):
    """Base for mapping errors."""


class MissingFieldError(MappingError):
    """Required field missing in response."""


class InvalidValueError(MappingError):
    """Invalid field value in input."""


_ORDER_TYPE_TO_DHAN: dict[OrderType, str] = {
    OrderType.LIMIT: "LIMIT",
    OrderType.MARKET: "MARKET",
    OrderType.STOP_LOSS: "SL",
    OrderType.STOP_LOSS_MARKET: "SL-M",
}

_DHAN_ORDER_TYPE_TO_DOMAIN: dict[str, OrderType] = {
    "LIMIT": OrderType.LIMIT,
    "MARKET": OrderType.MARKET,
    "SL": OrderType.STOP_LOSS,
    "SL-M": OrderType.STOP_LOSS_MARKET,
    "STOPLIMIT": OrderType.STOP_LOSS,
    "STOPMARKET": OrderType.STOP_LOSS_MARKET,
    "STOP LOSS": OrderType.STOP_LOSS,
    "STOP LOSS MARKET": OrderType.STOP_LOSS_MARKET,
}

# Canonical status mapping lives in scalpr.domain.order.BROKER_STATUS_TO_ORDER_STATE.
# This module re-exports it for backward compatibility.
_DHAN_STATUS_TO_STATE = BROKER_STATUS_TO_ORDER_STATE


# order_to_dhan_request v1 removed (REF-05 — dead code, superseded by v2)


def response_to_fill(response: dict, order: Order) -> Fill:
    order_id = response.get("orderId")
    if not order_id:
        raise MissingFieldError("response missing 'orderId'")

    qty = response.get("filledQuantity")
    if qty is None:
        qty = order.filled_quantity
    if not isinstance(qty, int):
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            qty = order.filled_quantity

    price_raw = response.get("tradedPrice") or response.get("fillPrice")
    price = order.avg_price if price_raw is None else Decimal(str(price_raw))

    return Fill(
        fill_id=f"f_{order_id}",
        order_id=order_id,
        symbol=order.symbol,
        side=order.side,
        quantity=qty,
        price=price,
        timestamp=datetime.now(timezone.utc),
    )


def order_status_from_dhan(dhan_status: str) -> OrderState:
    status = dhan_status.strip().upper()
    state = _DHAN_STATUS_TO_STATE.get(status)
    if state is None:
        raise InvalidValueError(f"Unknown Dhan status: {dhan_status!r}")
    return state


def transaction_type_from_side(side: OrderSide) -> str:
    if side == OrderSide.BUY:
        return "BUY"
    if side == OrderSide.SELL:
        return "SELL"
    raise InvalidValueError(f"Unknown order side: {side}")


def transaction_type_to_side(transaction_type: str) -> OrderSide:
    value = transaction_type.strip().upper()
    if value == "BUY":
        return OrderSide.BUY
    if value == "SELL":
        return OrderSide.SELL
    raise InvalidValueError(f"Unknown Dhan transactionType: {transaction_type!r}")


def order_book_entry_to_fill(
    entry: dict,
    local_order_id: str,
    delta_quantity: int,
    timestamp: datetime | None = None,
) -> Fill:
    """Build a Fill for the newly-executed quantity of an order-book row.

    `delta_quantity` is the increase since the last poll, not the cumulative
    filled quantity — publishing the cumulative figure would double-count the
    position on every poll.

    Uses the real Dhan order-book field names: `filledQty` and
    `averageTradedPrice` (with `tradedPrice` as a fallback for order-detail
    responses). `timestamp` comes from the injected clock; `datetime.now` is
    only a last-resort fallback for direct callers.
    """
    price_raw = entry.get("averageTradedPrice") or entry.get("tradedPrice")
    if price_raw is None:
        raise MissingFieldError("order book entry missing traded price")
    broker_order_id = entry.get("orderId")
    if not broker_order_id:
        raise MissingFieldError("order book entry missing 'orderId'")
    filled = entry.get("filledQty") or entry.get("filledQuantity") or 0
    return Fill(
        fill_id=f"f_{broker_order_id}_{filled}",
        order_id=local_order_id,
        symbol=str(entry.get("tradingSymbol", "")),
        side=transaction_type_to_side(str(entry.get("transactionType", "BUY"))),
        quantity=delta_quantity,
        price=Decimal(str(price_raw)),
        timestamp=timestamp or datetime.now(timezone.utc),
        exchange=str(entry.get("exchangeSegment", "")),
    )


def order_type_from_domain(order_type: OrderType) -> str:
    try:
        return _ORDER_TYPE_TO_DHAN[order_type]
    except KeyError as exc:
        raise InvalidValueError(f"Unknown order type: {order_type}") from exc


def raw_order_to_order(raw: dict[str, Any]) -> Order:
    status_str = raw.get("status", "").upper()
    state = OrderState.PENDING if not status_str else order_status_from_dhan(status_str)

    side_str = raw.get("side", "").upper()
    side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL

    type_str = raw.get("order_type", "").upper()
    order_type = _DHAN_ORDER_TYPE_TO_DOMAIN.get(type_str, OrderType.LIMIT)

    exchange_segment = raw.get("exchange_segment", "NSE_EQ").upper()
    if "MCX" in exchange_segment:
        exchange = Exchange.MCX
    elif "BSE" in exchange_segment:
        exchange = Exchange.BSE
    else:
        exchange = Exchange.NSE

    return Order(
        order_id=raw.get("order_id", ""),
        symbol=raw.get("symbol", ""),
        exchange=exchange,
        side=side,
        order_type=order_type,
        quantity=raw.get("quantity", 0),
        price=Decimal(str(raw.get("price", "0"))),
        trigger_price=Decimal(str(raw.get("trigger_price", "0"))),
        state=state,
        filled_quantity=raw.get("filled_quantity", 0),
        avg_price=Decimal(str(raw.get("traded_price", "0"))),
        product_type=raw.get("product_type", "INTRADAY"),
        validity=raw.get("validity", "DAY"),
        reject_reason=raw.get("reject_reason", ""),
        correlation_id=raw.get("correlation_id"),
    )


def raw_trade_to_fill(raw: dict[str, Any]) -> Fill:
    side_str = raw.get("side", "").upper()
    side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL

    trade_date_str = raw.get("trade_date", "")
    timestamp = None
    if trade_date_str:
        try:
            timestamp = datetime.fromisoformat(trade_date_str)
        except (ValueError, TypeError):
            pass

    from scalpr.adapters.dhan._resolver import SEGMENT_TO_EXCHANGE
    exchange = SEGMENT_TO_EXCHANGE.get(raw.get("exchange_segment", ""), "")

    return Fill(
        fill_id=raw.get("trade_id", ""),
        order_id=raw.get("order_id", ""),
        symbol=raw.get("symbol", ""),
        side=side,
        quantity=raw.get("quantity", 0),
        price=Decimal(str(raw.get("price", "0"))),
        timestamp=timestamp,
        exchange=exchange,
    )


_PRODUCT_TYPE_MAP: dict[str, str] = {
    "MIS": "INTRADAY",
    "CNC": "CNC",
    "MARGIN": "MARGIN",
    "MTF": "MTF",
    "CO": "CO",
    "BO": "BO",
}


def product_type_from_domain(product: str) -> str:
    try:
        return _PRODUCT_TYPE_MAP[product.upper()]
    except KeyError as exc:
        raise InvalidValueError(f"Unknown product type: {product!r}") from exc


def order_to_dhan_request_v2(
    order: Order,
    security_id: str,
    segment: str,
    client_id: str,
    product_type: str = "INTRADAY",
    after_market: bool = False,
    amo_time: str = "OPEN",
    bo_profit: float | None = None,
    bo_stop_loss: float | None = None,
    disclosed_qty: int = 0,
    tag: str | None = None,
) -> dict[str, Any]:
    if after_market and amo_time not in ("OPEN", "OPEN_30", "OPEN_60"):
        raise InvalidValueError(f"amo_time must be OPEN, OPEN_30, or OPEN_60, got {amo_time!r}")

    try:
        dhan_order_type = order_type_from_domain(order.order_type)
    except InvalidValueError as exc:
        raise InvalidValueError(f"Unknown order type: {order.order_type}") from exc

    if order.side not in (OrderSide.BUY, OrderSide.SELL):
        raise InvalidValueError(f"Unknown order side: {order.side}")

    payload: dict[str, Any] = {
        "dhanClientId": client_id,
        "correlationId": order.correlation_id or "",
        "transactionType": order.side.value,
        "exchangeSegment": segment,
        "productType": product_type,
        "orderType": dhan_order_type,
        "validity": order.validity,
        "securityId": security_id,
        "quantity": order.quantity,
        "disclosedQuantity": disclosed_qty,
        "price": str(order.price),
        "triggerPrice": str(order.trigger_price),
        "afterMarketOrder": after_market,
    }

    if after_market:
        payload["amoTime"] = amo_time

    if bo_profit is not None:
        payload["boProfitValue"] = bo_profit

    if bo_stop_loss is not None:
        payload["boStopLossValue"] = bo_stop_loss

    if tag:
        payload["correlationId"] = tag

    return payload
