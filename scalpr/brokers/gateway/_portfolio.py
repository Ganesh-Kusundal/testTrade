"""Portfolio and orders mixin for Gateway.

Provides portfolio operations: positions, holdings, funds, orders, trades.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from scalpr.brokers.contracts import Funds, Holding, Trade
from scalpr.domain.order import Order
from scalpr.domain.position import Position


class PortfolioMixin:
    """Mixin providing portfolio and order operations.

    Expects the composed Gateway class to provide _gateway attribute.
    """

    # Attribute provided by the composed Gateway class
    _gateway: Any

    def positions(self) -> list[Position]:
        """Fetch current open positions.

        Returns:
            List of Position domain objects
        """
        result: list[Position] = self._gateway.get_positions()
        return result

    def holdings(self) -> list[Holding]:
        """Fetch long-term delivery holdings.

        Returns:
            List of Holding dataclass objects
        """
        raw_holdings = self._gateway.get_holdings()

        # Map to canonical Holding model
        holdings = []
        for pos in raw_holdings:
            holdings.append(
                Holding(
                    symbol=pos.symbol,
                    exchange=pos.exchange.value
                    if hasattr(pos.exchange, "value")
                    else str(pos.exchange),
                    quantity=pos.quantity,
                    average_price=pos.avg_price,
                    current_price=pos.ltp,
                    pnl=pos.unrealised_pnl,
                )
            )

        return holdings

    def funds(self) -> Funds:
        """Fetch available margin limits and fund details.

        Returns:
            Funds dataclass with margin details
        """
        result = self._gateway.get_fund_limits()
        # Adapter may return Funds directly or a dict
        if isinstance(result, Funds):
            return result
        return Funds(
            available_margin=Decimal(str(result.get("available_margin", 0))),
            used_margin=Decimal(str(result.get("used_margin", 0))),
            total_balance=Decimal(str(result.get("total_balance", 0))),
            collateral=Decimal(str(result.get("collateral", 0))),
            realtime=result.get("realtime", True),
        )

    def orders(self) -> list[Order]:
        """Fetch the full orderbook.

        Returns:
            List of Order domain objects
        """
        result: list[Order] = self._gateway.get_orders()
        return result

    def trades(self) -> list[Trade]:
        """Fetch the day's tradebook (execution fills).

        Returns:
            List of Trade dataclass objects
        """
        raw_trades = self._gateway.get_tradebook()

        # Map to canonical Trade model
        trades = []
        for fill in raw_trades:
            trades.append(
                Trade(
                    trade_id=fill.fill_id,
                    order_id=fill.order_id,
                    symbol=fill.symbol,
                    exchange=fill.exchange,
                    side=fill.side,
                    quantity=fill.quantity,
                    price=fill.price,
                    timestamp=fill.timestamp,
                )
            )

        return trades
