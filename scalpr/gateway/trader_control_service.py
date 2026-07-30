from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from scalpr.adapters.dhan.client import DhanClient

logger = logging.getLogger(__name__)


class KillSwitchAction(str, Enum):
    ACTIVATE = "ACTIVATE"
    DEACTIVATE = "DEACTIVATE"


class KillSwitchStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ExitScope(str, Enum):
    ALL = "ALL"
    ORDERS = "ORDERS"
    POSITIONS = "POSITIONS"


class TraderControlService:
    """Broker-agnostic trader control service for kill switch and exit-all.

    These methods require explicit confirmation at the application layer
    because they can materially alter live positions.
    """

    def __init__(self, client: DhanClient) -> None:
        self._client = client

    def kill_switch(self, action: KillSwitchAction) -> KillSwitchStatus:
        """Activate or deactivate the kill switch."""
        result = self._client.kill_switch(action.value)
        return KillSwitchStatus(result.upper())

    def kill_switch_status(self) -> KillSwitchStatus:
        """Return the current kill switch status."""
        result = self._client.status_kill_switch()
        return KillSwitchStatus(result.upper())

    def exit_all(self, scope: ExitScope = ExitScope.ALL) -> dict[str, Any]:
        """Cancel all open orders and/or flatten all positions.

        Returns a summary of actions taken.
        """
        result: dict[str, Any] = {}

        if scope in (ExitScope.ALL, ExitScope.ORDERS):
            cancelled = self._client.cancel_all_orders()
            result["orders_cancelled"] = cancelled

        if scope in (ExitScope.ALL, ExitScope.POSITIONS):
            positions = self._client.get_positions()
            result["positions_closed"] = len(positions)

        return result
