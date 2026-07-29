"""Backward-compatible ``IBrokerGateway`` implementation wrapping ``DhanClient``.

This module bridges the old hexagonal-port architecture to the new
event-driven adapter. All existing consumers (OMS, execution, risk,
simulation) continue to receive the ``IBrokerGateway`` interface they
expect, while delegating all real work to ``DhanClient`` under the hood.

Once all consumers are migrated to ``DhanClient`` directly, this file
and :mod:`scalpr.brokers.broker_port` can be removed together.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from scalpr.adapters.dhan.client import DhanClient
from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import SimpleInstrumentId
from scalpr.domain.order import Order
from scalpr.domain.position import Position

logger = logging.getLogger(__name__)


class DhanBrokerGateway(IBrokerGateway):
    """Wraps ``DhanClient`` into the legacy ``IBrokerGateway`` interface.

    Each method delegates to the equivalent ``DhanClient`` method, with
    minimal adaptation for return-type compatibility.
    """

    def __init__(self, client: DhanClient) -> None:
        self._client = client
        self._connected = False

    # ── Lifecycle ──────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._client.start()
        self._connected = True
        logger.info("dhan_broker_gateway_connected")

    def disconnect(self) -> None:
        self._client.stop()
        self._connected = False
        logger.info("dhan_broker_gateway_disconnected")

    @property
    def connection(self) -> Any | None:
        return self._client if self._connected else None

    def adapters(self) -> dict[str, Any]:
        return {
            "resolver": self._client._resolver,
            "option_chain": self._client._option_chain,
            "historical": self._client._historical,
            "portfolio": self._client._portfolio,
            "greeks": self._client._greeks,
        }

    # ── ITradingPort ───────────────────────────────────────────────────

    def place_order(self, order: Order) -> Fill:
        order_id = self._client.place_order(order)
        fills = self._client.get_trade_book()
        for f in fills:
            if isinstance(f, Fill) and str(f.order_id) == order_id:
                return f
        raise RuntimeError(f"Order {order_id} placed but no fill found")

    def modify_order(self, order_id: str, price: Decimal, quantity: int) -> bool:
        return self._client.modify_order(order_id, price=float(price), quantity=quantity)

    def cancel_order(self, order_id: str) -> bool:
        return self._client.cancel_order(order_id)

    def get_order_status(self, order_id: str) -> Order:
        detail = self._client.get_order_detail(order_id)
        from scalpr.domain.order import Order, OrderSide, OrderType
        return Order(
            order_id=detail.get("orderId", order_id),
            symbol=detail.get("tradingSymbol", ""),
            exchange=self._client._resolver.resolve(detail.get("tradingSymbol", ""), detail.get("exchangeSegment", "NSE")).exchange if detail.get("tradingSymbol") else None,
            side=OrderSide.BUY if detail.get("transactionType") == "BUY" else OrderSide.SELL,
            order_type=OrderType(detail.get("orderType", "MARKET").lower()),
            quantity=int(detail.get("quantity", 0)),
            price=Decimal(str(detail.get("price", 0))),
        )

    def get_orders(self) -> list[Order]:
        orders_data = self._client._http_client.get("/orders", bucket="portfolio")
        from scalpr.domain.order import Order, OrderSide, OrderType
        return [
            Order(
                order_id=o.get("orderId", ""),
                symbol=o.get("tradingSymbol", ""),
                exchange=None,
                side=OrderSide.BUY if o.get("transactionType") == "BUY" else OrderSide.SELL,
                order_type=OrderType(o.get("orderType", "MARKET").lower()),
                quantity=int(o.get("quantity", 0)),
                price=Decimal(str(o.get("price", 0))),
            )
            for o in (orders_data.get("data") or orders_data if isinstance(orders_data, list) else [])
        ]

    def get_tradebook(self) -> list[Fill]:
        return self._client.get_trade_book()

    def square_off_all(self) -> list[Fill]:
        positions = self._client.get_positions()
        fills = []
        for pos in positions:
            if pos.quantity != 0:
                try:
                    self._client.place_order(Order(
                        order_id="",
                        symbol=pos.symbol,
                        exchange=pos.exchange,
                        side=pos.position_side.opposite(),
                        order_type=pos.order_type if hasattr(pos, 'order_type') else None,
                        quantity=abs(pos.quantity),
                        price=pos.avg_price,
                    ))
                except Exception as exc:
                    logger.error("square_off_failed: symbol=%s error=%s", pos.symbol, exc)
        return fills

    # ── IMarketDataPort ────────────────────────────────────────────────

    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Decimal:
        return Decimal(str(self._client._historical.get_ltp(symbol, exchange)))

    def get_quote(self, symbol: str, exchange: str = "NSE") -> dict[str, Any]:
        return self._client.get_quote(SimpleInstrumentId(symbol=symbol, exchange=exchange))

    def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        interval = 5
        if timeframe in ("1m", "1"):
            interval = 1
        elif timeframe in ("5m", "5"):
            interval = 5
        elif timeframe in ("15m", "15"):
            interval = 15
        elif timeframe in ("1D", "DAY", "1d"):
            return self._client.get_daily(symbol, exchange, from_date.isoformat(), to_date.isoformat())
        return self._client.get_intraday(symbol, exchange, interval, from_date.isoformat(), to_date.isoformat())

    # ── IAccountPort ───────────────────────────────────────────────────

    def get_positions(self) -> list[Position]:
        return self._client.get_positions()

    def get_holdings(self) -> list[Position]:
        raw = self._client.get_holdings()
        from scalpr.domain.position import PositionSide
        from scalpr.domain.values import ZERO
        result = []
        for item in raw if isinstance(raw, list) else raw.get("data", []):
            result.append(Position(
                symbol=item.get("tradingSymbol", ""),
                exchange=self._client._resolver.resolve(item.get("tradingSymbol", ""), "NSE").exchange if item.get("tradingSymbol") else None,
                quantity=int(item.get("totalQty", 0)),
                avg_price=Decimal(str(item.get("avgCostPrice", 0))),
                ltp=Decimal(str(item.get("lastTradedPrice", 0))),
                position_side=PositionSide.LONG,
            ))
        return result

    def get_margins(self) -> dict[str, Any]:
        return self._client.get_funds()

    def get_fund_limits(self) -> dict[str, Any]:
        return self._client.get_funds()
