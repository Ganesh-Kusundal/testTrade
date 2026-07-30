from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.contracts import Funds, Holding
from scalpr.domain.position import Position, PositionSide
from scalpr.gateway.portfolio_service import PortfolioService


class TestPortfolioServiceHoldings:
    def test_holdings_returns_domain_objects(self):
        client = MagicMock(spec=DhanClient)
        client.get_holdings.return_value = [
            {"symbol": "TCS", "exchange": "NSE", "quantity": 10,
             "averagePrice": "2500", "ltp": "2510", "pnl": "100", "pnlPercent": "4.0"},
        ]
        svc = PortfolioService(client)
        result = svc.holdings()
        assert len(result) == 1
        assert isinstance(result[0], Holding)
        assert result[0].symbol == "TCS"
        assert result[0].quantity == 10
        assert result[0].average_price == Decimal("2500")

    def test_holdings_empty(self):
        client = MagicMock(spec=DhanClient)
        client.get_holdings.return_value = []
        svc = PortfolioService(client)
        assert svc.holdings() == []

    def test_holdings_from_dict(self):
        client = MagicMock(spec=DhanClient)
        client.get_holdings.return_value = {"holdings": [
            {"symbol": "RELIANCE", "exchange": "NSE", "quantity": 5,
             "averagePrice": "2400", "ltp": "2450", "pnl": "250", "pnlPercent": "10.4"},
        ]}
        svc = PortfolioService(client)
        result = svc.holdings()
        assert len(result) == 1
        assert result[0].symbol == "RELIANCE"


class TestPortfolioServicePositions:
    def test_positions_returns_domain_objects(self):
        client = MagicMock(spec=DhanClient)
        pos = Position(
            symbol="TCS", exchange=__import__("scalpr.domain.instrument", fromlist=["Exchange"]).Exchange.NSE,
            quantity=10, avg_price=Decimal("2500"), ltp=Decimal("2510"),
            unrealised_pnl=Decimal("100"), position_side=PositionSide.LONG,
        )
        client.get_positions.return_value = [pos]
        svc = PortfolioService(client)
        result = svc.positions()
        assert len(result) == 1
        assert isinstance(result[0], Position)
        assert result[0].symbol == "TCS"
        assert result[0].quantity == 10


class TestPortfolioServiceFundLimits:
    def test_fund_limits_returns_funds(self):
        client = MagicMock(spec=DhanClient)
        client.get_funds.return_value = {
            "available": "50000", "used": "10000", "total": "60000", "collateral": "5000",
        }
        svc = PortfolioService(client)
        result = svc.fund_limits()
        assert isinstance(result, Funds)
        assert result.available_margin == Decimal("50000")
        assert result.used_margin == Decimal("10000")
        assert result.total_balance == Decimal("60000")
        assert result.collateral == Decimal("5000")

    def test_fund_limits_empty(self):
        client = MagicMock(spec=DhanClient)
        client.get_funds.return_value = {}
        svc = PortfolioService(client)
        result = svc.fund_limits()
        assert isinstance(result, Funds)
        assert result.available_margin == Decimal("0")
