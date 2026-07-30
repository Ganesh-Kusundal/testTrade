from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.contracts import Funds
from scalpr.gateway.account_service import AccountService


class TestAccountServiceFundLimits:
    def test_fund_limits_returns_funds(self):
        client = MagicMock(spec=DhanClient)
        client.get_funds.return_value = {
            "available": "50000", "used": "10000", "total": "60000", "collateral": "5000",
        }
        svc = AccountService(client)
        result = svc.fund_limits()
        assert isinstance(result, Funds)
        assert result.available_margin == Decimal("50000")
        assert result.used_margin == Decimal("10000")
        assert result.total_balance == Decimal("60000")

    def test_fund_limits_empty(self):
        client = MagicMock(spec=DhanClient)
        client.get_funds.return_value = {}
        svc = AccountService(client)
        result = svc.fund_limits()
        assert result.available_margin == Decimal("0")


class TestAccountServiceMargin:
    def test_margin_calls_client(self):
        client = MagicMock(spec=DhanClient)
        client.margin_calculator.return_value = {"margin": "5000"}
        svc = AccountService(client)
        result = svc.margin(
            security_id="12345", exchange_segment="NSE_EQ",
            transaction_type="BUY", quantity=10,
            product_type="INTRADAY", price=2500.0,
        )
        assert result == {"margin": "5000"}
        client.margin_calculator.assert_called_once()
