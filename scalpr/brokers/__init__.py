"""Backward-compatible broker module — shims for migration.

Do NOT import from this module in new code. Import from
``scalpr.adapters.dhan.*`` or ``scalpr.domain.*`` instead.

This module will be removed once all consumers are migrated.
"""
from __future__ import annotations

from scalpr.brokers.broker_port import IBrokerGateway, ITradingPort, IMarketDataPort, IAccountPort


class BrokerRegistry:
    """Legacy broker registry — returns 'dhan' as the only broker."""

    @staticmethod
    def list_brokers() -> list[str]:
        return ["dhan"]

    @staticmethod
    def get_broker(name: str) -> str | None:
        return "dhan" if name == "dhan" else None


class Gateway:
    """Legacy Gateway wrapper — creates a DhanClient-based gateway.

    Usage::
        gw = Gateway()
        port = gw.gateway  # IBrokerGateway-compatible
    """

    def __init__(self, broker: str = "dhan") -> None:
        import os
        from scalpr.adapters.dhan.client import DhanClient
        from scalpr.brokers.broker_gateway import DhanBrokerGateway
        from scalpr.engine.clock import LiveClock
        from scalpr.engine.message_bus import MessageBus

        client_id = os.environ.get("DHAN_CLIENT_ID", "")
        access_token = os.environ.get("DHAN_ACCESS_TOKEN", "")
        bus = MessageBus()
        clock = LiveClock()
        self._client = DhanClient(bus, clock, {
            "client_id": client_id,
            "access_token": access_token,
            "totp_secret": os.environ.get("DHAN_TOTP_SECRET", ""),
            "pin": os.environ.get("DHAN_PIN", "1111"),
            "csv_path": os.environ.get("DHAN_INSTRUMENT_CSV", "instrument.csv"),
        })
        self.gateway = DhanBrokerGateway(self._client)
        self.gateway.connect()

    def close(self) -> None:
        self.gateway.disconnect()
