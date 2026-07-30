from __future__ import annotations

from unittest.mock import MagicMock

from scalpr.adapters.dhan.client import DhanClient
from scalpr.gateway.trader_control_service import (
    ExitScope,
    KillSwitchAction,
    KillSwitchStatus,
    TraderControlService,
)


class TestTraderControlService:
    def test_kill_switch_activates(self):
        client = MagicMock(spec=DhanClient)
        client.kill_switch.return_value = "ACTIVE"
        svc = TraderControlService(client)
        result = svc.kill_switch(KillSwitchAction.ACTIVATE)
        assert result == KillSwitchStatus.ACTIVE
        client.kill_switch.assert_called_once_with("ACTIVATE")

    def test_kill_switch_status(self):
        client = MagicMock(spec=DhanClient)
        client.status_kill_switch.return_value = "ACTIVE"
        svc = TraderControlService(client)
        result = svc.kill_switch_status()
        assert result == KillSwitchStatus.ACTIVE

    def test_exit_all_cancels_orders_and_closes_positions(self):
        client = MagicMock(spec=DhanClient)
        client.cancel_all_orders.return_value = 5
        client.get_positions.return_value = [MagicMock(), MagicMock()]
        svc = TraderControlService(client)
        result = svc.exit_all(ExitScope.ALL)
        assert result["orders_cancelled"] == 5
        assert result["positions_closed"] == 2

    def test_exit_orders_only(self):
        client = MagicMock(spec=DhanClient)
        client.cancel_all_orders.return_value = 3
        svc = TraderControlService(client)
        result = svc.exit_all(ExitScope.ORDERS)
        assert result["orders_cancelled"] == 3
        assert "positions_closed" not in result
