"""Order management REST routes — wired to real dependencies.

C3 fail-closed: broker unavailable → 503, adapter failure → 502.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderType
from scalpr.engine.execution_engine import SubmitOrder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


class PlaceOrderBody(BaseModel):
    symbol: str
    exchange: str = "NSE"
    side: str
    order_type: str = "LIMIT"
    quantity: int
    price: float | None = None
    trigger_price: float | None = None
    product_type: str = "INTRADAY"
    validity: str = "DAY"


def _require_preferred(request: Request) -> tuple[Any, str]:
    event_system = getattr(request.app.state, "event_system", None)
    if event_system:
        return event_system, "event_system"
    gateway = request.app.state.gateway
    if gateway and gateway.is_connected():
        return gateway, "gateway"
    raise HTTPException(status_code=503, detail="broker unavailable")


@router.get("/")
async def get_orders(request: Request) -> Any:
    client, source = _require_preferred(request)
    try:
        if source == "event_system":
            return client.get_trade_book()
        return client.get_orders() if hasattr(client, "get_orders") else []
    except Exception as exc:
        logger.error("orders_fetch_failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc


@router.post("/")
async def place_order(body: PlaceOrderBody, request: Request) -> Any:
    event_system = getattr(request.app.state, "event_system", None)
    if event_system:
        bus = event_system["bus"]
        try:
            exchange = Exchange(body.exchange.upper())
            side = OrderSide(body.side.upper())
            order_type = OrderType(body.order_type.upper())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        order = Order(
            order_id=str(uuid4()),
            symbol=body.symbol.upper(),
            exchange=exchange,
            side=side,
            order_type=order_type,
            quantity=body.quantity,
            price=Decimal(str(body.price or 0)),
            trigger_price=Decimal(str(body.trigger_price or 0)),
            product_type=body.product_type.upper(),
            validity=body.validity.upper(),
        )
        try:
            bus.publish("exec.command.submit.dhan", SubmitOrder(order=order))
        except Exception as exc:
            logger.error("order_submit_failed: %s", exc)
            raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc
        return {"order_id": order.order_id, "status": "submitted"}

    gateway = request.app.state.gateway
    if not gateway or not gateway.is_connected():
        raise HTTPException(status_code=503, detail="broker unavailable")
    try:
        order_id = gateway.place_order(
            symbol=body.symbol.upper(),
            exchange=body.exchange.upper(),
            side=body.side.upper(),
            order_type=body.order_type.upper(),
            quantity=body.quantity,
            price=Decimal(str(body.price or 0)),
            trigger_price=Decimal(str(body.trigger_price or 0)),
            product_type=body.product_type.upper(),
        )
    except Exception as exc:
        logger.error("order_submit_failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"broker error: {exc}") from exc
    return {"order_id": order_id, "status": "submitted"}


@router.get("/fills")
async def get_fills(request: Request) -> Any:
    raise HTTPException(status_code=501, detail="fills endpoint not implemented")
