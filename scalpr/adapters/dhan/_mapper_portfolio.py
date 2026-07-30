from __future__ import annotations

from decimal import Decimal
from typing import Any

from scalpr.adapters.dhan._mapper_orders import InvalidValueError
from scalpr.domain.instrument import Exchange
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.domain.values import ZERO

OptionChain = dict[str, Any]


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
