from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType


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

_DHAN_STATUS_TO_STATE: dict[str, OrderState] = {
    "PENDING": OrderState.PENDING,
    "OPEN": OrderState.OPEN,
    "PARTIALLY FILLED": OrderState.PARTIALLY_FILLED,
    "FILLED": OrderState.FILLED,
    "TRADED": OrderState.FILLED,
    "CANCELLED": OrderState.CANCELLED,
    "REJECTED": OrderState.REJECTED,
    "EXPIRED": OrderState.EXPIRED,
    "TRIGGER PENDING": OrderState.PENDING,
}


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


def order_type_from_domain(order_type: OrderType) -> str:
    try:
        return _ORDER_TYPE_TO_DHAN[order_type]
    except KeyError:
        raise InvalidValueError(f"Unknown order type: {order_type}")


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
    except KeyError:
        raise InvalidValueError(f"Unknown product type: {product!r}")


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
    except InvalidValueError:
        raise InvalidValueError(f"Unknown order type: {order.order_type}")

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
