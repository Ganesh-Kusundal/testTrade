from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, TypedDict

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange, InstrumentId
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.domain.tick import Tick
from scalpr.domain.values import ZERO


class MappingError(Exception):
    """Base for mapping errors."""


class MissingFieldError(MappingError):
    """Required field missing in response."""


class InvalidValueError(MappingError):
    """Invalid field value in input."""


class Quote(TypedDict):
    symbol: str
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    change: Decimal
    change_percent: Decimal
    oi: int


QuoteTick = Tick
OptionChain = dict[str, Any]


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


def order_to_dhan_request(
    order: Order,
    security_id: str,
    segment: str,
    client_id: str,
) -> dict[str, Any]:
    try:
        dhan_order_type = _ORDER_TYPE_TO_DHAN[order.order_type]
    except KeyError:
        raise InvalidValueError(f"Unknown order type: {order.order_type}")

    if order.side not in (OrderSide.BUY, OrderSide.SELL):
        raise InvalidValueError(f"Unknown order side: {order.side}")

    return {
        "dhanClientId": client_id,
        "correlationId": order.correlation_id or "",
        "transactionType": order.side.value,
        "exchangeSegment": segment,
        "productType": order.product_type,
        "orderType": dhan_order_type,
        "quantity": order.quantity,
        "price": str(order.price),
        "triggerPrice": str(order.trigger_price),
        "securityId": security_id,
        "validity": order.validity,
    }


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


def to_position(data: dict) -> Position:
    symbol = data.get("symbol", "")
    exchange_str = data.get("exchange", "NSE")
    try:
        exchange = Exchange(exchange_str.upper())
    except ValueError:
        exchange = Exchange.NSE

    raw_qty = data.get("quantity", 0)
    try:
        quantity = int(raw_qty)
    except (TypeError, ValueError):
        raise InvalidValueError(f"Invalid quantity: {raw_qty}")

    try:
        avg_price = Decimal(str(data.get("avgPrice", "0")))
    except Exception as e:
        raise InvalidValueError(f"Invalid avgPrice: {data.get('avgPrice')}") from e

    try:
        ltp = Decimal(str(data.get("ltp", "0")))
    except Exception as e:
        raise InvalidValueError(f"Invalid ltp: {data.get('ltp')}") from e

    try:
        realised_pnl = Decimal(str(data.get("realizedPnl", "0")))
    except Exception as e:
        raise InvalidValueError(f"Invalid realizedPnl: {data.get('realizedPnl')}") from e

    if quantity > 0:
        side = PositionSide.LONG
        state = PositionState.OPEN
    elif quantity < 0:
        side = PositionSide.SHORT
        state = PositionState.OPEN
    else:
        side = PositionSide.FLAT
        state = PositionState.FLAT

    if quantity > 0:
        unrealised = Decimal(quantity) * (ltp - avg_price)
    elif quantity < 0:
        unrealised = Decimal(abs(quantity)) * (avg_price - ltp)
    else:
        unrealised = ZERO

    return Position(
        symbol=symbol,
        exchange=exchange,
        quantity=quantity,
        avg_price=avg_price,
        ltp=ltp,
        unrealised_pnl=unrealised,
        realised_pnl=realised_pnl,
        position_side=side,
        state=state,
    )


def to_quote(data: dict, instrument_id: InstrumentId) -> Quote | QuoteTick:
    if "type" in data and data.get("security_id") is not None:
        return _ws_tick_from_data(data, instrument_id)
    return _rest_quote_from_data(data, instrument_id)


def _rest_quote_from_data(data: dict, instrument_id: InstrumentId) -> Quote:
    ohlc = data.get("ohlc", {})
    close = Decimal(str(ohlc.get("close", 0)))
    ltp = Decimal(str(data.get("last_price", 0)))
    net_change = Decimal(str(data.get("net_change", 0)))
    change_percent = (net_change / close * 100) if close else ZERO

    symbol = str(instrument_id).split(":")[0]

    return Quote(
        symbol=symbol,
        ltp=ltp,
        open=Decimal(str(ohlc.get("open", 0))),
        high=Decimal(str(ohlc.get("high", 0))),
        low=Decimal(str(ohlc.get("low", 0))),
        close=close,
        volume=int(data.get("volume", 0)),
        change=net_change,
        change_percent=change_percent,
        oi=int(data.get("oi", 0)),
    )


def _ws_tick_from_data(data: dict, instrument_id: InstrumentId) -> QuoteTick:
    symbol = str(instrument_id).split(":")[0]
    ltp = Decimal(str(data.get("LTP", "0")))

    depth = data.get("depth") or []
    if depth:
        bid = Decimal(str(depth[0].get("bid_price", "0")))
        ask = Decimal(str(depth[0].get("ask_price", "0")))
    else:
        bid = ask = ZERO

    raw_vol = data.get("volume", 0)
    cum_vol = int(raw_vol) if raw_vol is not None else 0

    return Tick(
        symbol=symbol,
        ltp=ltp,
        bid=bid,
        ask=ask,
        delta_volume=cum_vol,
        cumulative_volume=cum_vol,
        exchange_timestamp=datetime.now(timezone.utc),
    )


def to_option_chain(data: list[dict]) -> list[OptionChain]:
    result: list[OptionChain] = []
    for leg in data:
        strike = Decimal(str(leg.get("strike", 0)))
        for leg_key, side in (("ce", "CE"), ("pe", "PE")):
            side_data = leg.get(leg_key)
            if side_data is None:
                continue
            greeks = side_data.get("greeks", {})
            sid = side_data.get("security_id")
            result.append({
                "symbol": side_data.get("symbol", ""),
                "security_id": int(sid) if sid is not None else None,
                "strike": strike,
                "option_type": side,
                "bid": Decimal(str(side_data.get("top_bid_price", 0))),
                "bid_qty": int(side_data.get("top_bid_quantity", 0) or 0),
                "ask": Decimal(str(side_data.get("top_ask_price", 0))),
                "ask_qty": int(side_data.get("top_ask_quantity", 0) or 0),
                "oi": int(side_data.get("oi", 0)),
                "volume": int(side_data.get("volume", 0)),
                "iv": side_data.get("implied_volatility"),
                "ltp": Decimal(str(side_data.get("last_price", 0))),
                "delta": greeks.get("delta"),
                "theta": greeks.get("theta"),
                "gamma": greeks.get("gamma"),
                "vega": greeks.get("vega"),
            })
    return result


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
    from scalpr.domain.instrument import Exchange
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

    from scalpr.brokers.dhan.resolution import SEGMENT_TO_EXCHANGE
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


# ── Product type mapping ─────────────────────────────────────────

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


# ── Extended order request (v2) ──────────────────────────────────


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


# ── Order report / trade mapping ─────────────────────────────────

ORDER_REPORT_FIELDS: list[str] = [
    "orderId", "symbol", "exchangeSegment", "transactionType",
    "orderType", "quantity", "filledQuantity", "price", "triggerPrice",
    "tradedPrice", "status", "productType", "validity", "rejectReason",
    "traded_at", "tradedTime", "createdAt", "createAt",
]


def order_report_to_dict(response: dict) -> dict:
    return {
        "order_id": response.get("orderId", ""),
        "symbol": response.get("tradingSymbol", response.get("symbol", "")),
        "exchange_segment": response.get("exchangeSegment", ""),
        "side": response.get("transactionType", ""),
        "order_type": response.get("orderType", ""),
        "quantity": response.get("quantity", 0),
        "filled_quantity": response.get("filledQuantity", 0),
        "price": response.get("price", "0"),
        "trigger_price": response.get("triggerPrice", "0"),
        "traded_price": response.get("tradedPrice", "0"),
        "status": response.get("status", ""),
        "product_type": response.get("productType", ""),
        "validity": response.get("validity", ""),
        "reject_reason": response.get("rejectReason", ""),
        "traded_at": response.get("traded_at") or response.get("tradedTime", ""),
        "created_at": response.get("createdAt") or response.get("createAt", ""),
    }


TRADE_FIELDS: list[str] = [
    "tradeId", "orderId", "symbol", "exchangeSegment",
    "transactionType", "quantity", "price", "tradeDateTime", "traded_at",
]


def trade_to_domain(trade: dict) -> dict:
    return {
        "trade_id": trade.get("tradeId", ""),
        "order_id": trade.get("orderId", ""),
        "symbol": trade.get("tradingSymbol", trade.get("symbol", "")),
        "exchange_segment": trade.get("exchangeSegment", ""),
        "side": trade.get("transactionType", ""),
        "quantity": trade.get("quantity", 0),
        "price": trade.get("price", "0"),
        "traded_at": trade.get("tradeDateTime") or trade.get("traded_at", ""),
    }


# ── Kill switch ──────────────────────────────────────────────────


_KILL_SWITCH_MAP: dict[str, str] = {
    "ON": "ACTIVATE",
    "ACTIVATE": "ACTIVATE",
    "OFF": "DEACTIVATE",
    "DEACTIVATE": "DEACTIVATE",
}


# ── Margin calculator ─────────────────────────────────────────────


def margin_calc_to_dhan_request(
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    product_type: str,
    price: float,
    trigger_price: float = 0,
) -> dict[str, Any]:
    if transaction_type.upper() not in ("BUY", "SELL"):
        raise InvalidValueError(f"transaction_type must be BUY or SELL, got {transaction_type!r}")
    payload: dict[str, Any] = {
        "securityId": security_id,
        "exchangeSegment": exchange_segment.upper(),
        "transactionType": transaction_type.upper(),
        "quantity": int(quantity),
        "productType": product_type.upper(),
        "price": float(price),
    }
    if trigger_price > 0:
        payload["triggerPrice"] = float(trigger_price)
    return payload


def kill_switch_to_dhan(action: str) -> dict[str, str]:
    if not action or not isinstance(action, str):
        raise InvalidValueError(
            f"Invalid kill switch action: {action!r}. Use ON/OFF or ACTIVATE/DEACTIVATE"
        )
    mapped = _KILL_SWITCH_MAP.get(action.upper())
    if mapped is None:
        raise InvalidValueError(
            f"Invalid kill switch action: {action!r}. Use ON/OFF or ACTIVATE/DEACTIVATE"
        )
    return {"action": mapped}


# ── Super orders ─────────────────────────────────────────────────


def super_order_to_dhan_request(
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    order_type: str,
    product_type: str,
    price: float,
    target_price: float = 0.0,
    stop_loss_price: float = 0.0,
    trailing_jump: float = 0.0,
    tag: str | None = None,
) -> dict[str, Any]:
    if transaction_type.upper() not in ("BUY", "SELL"):
        raise InvalidValueError(f"transaction_type must be BUY or SELL, got {transaction_type!r}")
    if quantity <= 0:
        raise InvalidValueError(f"quantity must be > 0, got {quantity}")
    if price <= 0:
        raise InvalidValueError(f"price must be > 0, got {price}")

    payload: dict[str, Any] = {
        "transactionType": transaction_type.upper(),
        "exchangeSegment": exchange_segment.upper(),
        "productType": product_type.upper(),
        "orderType": order_type.upper(),
        "securityId": security_id,
        "quantity": int(quantity),
        "price": float(price),
        "targetPrice": float(target_price),
        "stopLossPrice": float(stop_loss_price),
        "trailingJump": float(trailing_jump),
    }
    if tag:
        payload["correlationId"] = tag
    return payload


# ── Forever orders ───────────────────────────────────────────────


def forever_order_to_dhan_request(
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    price: float,
    trigger_price: float,
    order_type: str,
    product_type: str,
    validity: str = "DAY",
    order_flag: str = "SINGLE",
    disclosed_quantity: int = 0,
    price1: float = 0.0,
    trigger_price1: float = 0.0,
    quantity1: int = 0,
    tag: str | None = None,
    symbol: str = "",
) -> dict[str, Any]:
    if transaction_type.upper() not in ("BUY", "SELL"):
        raise InvalidValueError(f"transaction_type must be BUY or SELL, got {transaction_type!r}")
    if quantity <= 0:
        raise InvalidValueError(f"quantity must be > 0, got {quantity}")
    if order_flag.upper() not in ("SINGLE", "OCO"):
        raise InvalidValueError(f"order_flag must be SINGLE or OCO, got {order_flag!r}")
    if validity.upper() not in ("DAY", "IOC", "GTD"):
        raise InvalidValueError(f"validity must be DAY, IOC, or GTD, got {validity!r}")

    payload: dict[str, Any] = {
        "orderFlag": order_flag.upper(),
        "transactionType": transaction_type.upper(),
        "exchangeSegment": exchange_segment.upper(),
        "productType": product_type.upper(),
        "orderType": order_type.upper(),
        "validity": validity.upper(),
        "tradingSymbol": symbol,
        "securityId": security_id,
        "quantity": int(quantity),
        "disclosedQuantity": int(disclosed_quantity),
        "price": float(price),
        "triggerPrice": float(trigger_price),
        "price1": float(price1),
        "triggerPrice1": float(trigger_price1),
        "quantity1": int(quantity1),
    }
    if tag:
        payload["correlationId"] = tag
    return payload


# ── Conditional triggers ─────────────────────────────────────────


def conditional_trigger_to_dhan_request(
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    price: float,
    trigger_price: float,
    order_type: str,
    product_type: str,
    trigger_type: str = "PRICE_TRIGGER",
    validity: str = "DAY",
    disclosed_quantity: int = 0,
    tag: str | None = None,
) -> dict[str, Any]:
    if transaction_type.upper() not in ("BUY", "SELL"):
        raise InvalidValueError(f"transaction_type must be BUY or SELL, got {transaction_type!r}")
    if quantity <= 0:
        raise InvalidValueError(f"quantity must be > 0, got {quantity}")
    if trigger_price <= 0:
        raise InvalidValueError(f"trigger_price must be > 0, got {trigger_price}")
    if validity.upper() not in ("DAY", "IOC", "GTD", "GTC"):
        raise InvalidValueError(f"validity must be DAY, IOC, GTD, or GTC, got {validity!r}")

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
    }
    if tag:
        payload["correlationId"] = tag
    return payload
