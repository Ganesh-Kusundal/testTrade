from __future__ import annotations

from typing import Any

from scalpr.adapters.dhan._mapper_orders import InvalidValueError

_KILL_SWITCH_MAP: dict[str, str] = {
    "ON": "ACTIVATE",
    "ACTIVATE": "ACTIVATE",
    "OFF": "DEACTIVATE",
    "DEACTIVATE": "DEACTIVATE",
}


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
    comparison_type: str = "PRICE_WITH_VALUE",
    operator: str | None = None,
    time_frame: str = "DAY",
    comparing_value: float | None = None,
    indicator_name: str | None = None,
    comparing_indicator_name: str | None = None,
    frequency: str = "ONCE",
    exp_date: str | None = None,
    user_note: str = "",
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
    return payload
