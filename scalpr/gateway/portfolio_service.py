from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from scalpr.domain.contracts import BrokerClientProtocol, Funds, Holding
from scalpr.domain.position import Position

logger = logging.getLogger(__name__)


class PortfolioService:
    """Broker-agnostic portfolio service returning domain objects."""

    def __init__(self, client: BrokerClientProtocol) -> None:
        self._client = client

    def holdings(self) -> list[Holding]:
        """Return holdings as domain objects."""
        raw = self._client.get_holdings()
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = raw.get("holdings", raw.get("data", []))
        else:
            items = []
        return [_to_holding(item) for item in items]

    def positions(self) -> list[Position]:
        """Return positions as domain objects (already domain objects from adapter)."""
        return self._client.get_positions()

    def fund_limits(self) -> Funds:
        """Return fund limits as domain object."""
        raw = self._client.get_funds()
        if isinstance(raw, dict):
            return _to_funds(raw)
        return Funds(
            available_margin=Decimal("0"),
            used_margin=Decimal("0"),
            total_balance=Decimal("0"),
        )


def _to_holding(data: dict[str, Any]) -> Holding:
    return Holding(
        symbol=data.get("symbol", data.get("tradingSymbol", "")),
        exchange=data.get("exchange", "NSE"),
        quantity=int(data.get("quantity", data.get("qty", 0))),
        average_price=Decimal(str(data.get("averagePrice", data.get("avgPrice", 0)))),
        current_price=Decimal(str(data.get("ltp", data.get("lastPrice", 0)))),
        pnl=Decimal(str(data.get("pnl", data.get("unrealisedPnl", 0)))),
        pnl_percent=Decimal(str(data.get("pnlPercent", data.get("pnlPercentage", 0)))),
    )


def _to_funds(data: dict[str, Any]) -> Funds:
    return Funds(
        available_margin=Decimal(str(data.get("available", data.get("availableMargin", 0)))),
        used_margin=Decimal(str(data.get("used", data.get("usedMargin", 0)))),
        total_balance=Decimal(str(data.get("total", data.get("totalBalance", 0)))),
        collateral=Decimal(str(data.get("collateral", 0))),
    )
