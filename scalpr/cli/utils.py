"""Shared CLI utilities."""

import os

from rich.console import Console

from scalpr.engine.clock import LiveClock
from scalpr.engine.message_bus import MessageBus

console = Console()


def _make_dhan_client() -> object | None:
    """Create a DhanClient from environment variables, or None if missing."""
    client_id = os.environ.get("DHAN_CLIENT_ID", "")
    access_token = os.environ.get("DHAN_ACCESS_TOKEN", "")
    if not (client_id and access_token):
        return None
    from scalpr.adapters.dhan.client import DhanClient
    from scalpr.brokers.broker_gateway import DhanBrokerGateway

    bus = MessageBus()
    clock = LiveClock()
    config = {
        "client_id": client_id,
        "access_token": access_token,
        "totp_secret": os.environ.get("DHAN_TOTP_SECRET", ""),
        "pin": os.environ.get("DHAN_PIN", "1111"),
        "csv_path": os.environ.get("DHAN_INSTRUMENT_CSV", "instrument.csv"),
    }
    client = DhanClient(bus, clock, config)
    gateway = DhanBrokerGateway(client)
    gateway.connect()
    return gateway


def get_gateway(broker: str = "dhan") -> object | None:
    """Create and connect a DhanBrokerGateway from environment variables.

    Args:
        broker: Ignored (kept for backward compat).

    Returns:
        Connected DhanBrokerGateway instance, or None if credentials missing.
    """
    return _make_dhan_client()
