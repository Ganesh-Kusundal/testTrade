from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from scalpr.domain.contracts import BrokerClientProtocol, Funds

logger = logging.getLogger(__name__)


class AccountService:
    """Broker-agnostic account service returning domain objects."""

    def __init__(self, client: BrokerClientProtocol) -> None:
        self._client = client

    def fund_limits(self) -> Funds:
        """Return fund limits as domain object."""
        raw = self._client.get_funds()
        if isinstance(raw, dict):
            return Funds(
                available_margin=Decimal(str(raw.get("available", raw.get("availableMargin", 0)))),
                used_margin=Decimal(str(raw.get("used", raw.get("usedMargin", 0)))),
                total_balance=Decimal(str(raw.get("total", raw.get("totalBalance", 0)))),
                collateral=Decimal(str(raw.get("collateral", 0))),
            )
        return Funds(
            available_margin=Decimal("0"),
            used_margin=Decimal("0"),
            total_balance=Decimal("0"),
        )

    def margin(self, security_id: str, exchange_segment: str, transaction_type: str,
               quantity: int, product_type: str, price: float,
               trigger_price: float = 0) -> dict[str, Any]:
        """Calculate margin requirements for a proposed order."""
        return self._client.margin_calculator(
            security_id, exchange_segment, transaction_type,
            quantity, product_type, price, trigger_price,
        )
