"""Shared CLI utilities."""

import os

from rich.console import Console

from scalpr.brokers.gateway import Gateway
from scalpr.engine.clock import LiveClock
from scalpr.engine.message_bus import MessageBus

console = Console()


def _make_dhan_client() -> object | None:
    """Create a DhanClient from environment variables, or None if missing."""
    client_id = os.environ.get("DHAN_CLIENT_ID", "")
    access_token = os.environ.get("DHAN_ACCESS_TOKEN", "")
    totp_secret = os.environ.get("DHAN_TOTP_SECRET", "")
    if not (client_id and access_token and totp_secret):
        return None
    from scalpr.adapters.dhan.client import DhanClient

    bus = MessageBus()
    clock = LiveClock()
    config = {
        "client_id": client_id,
        "access_token": access_token,
        "totp_secret": totp_secret,
        "csv_path": os.environ.get("DHAN_INSTRUMENT_CSV", "instrument.csv"),
    }
    client = DhanClient(bus, clock, config)
    client.start()
    return client


def get_gateway(broker: str = "dhan") -> object:
    """Create and connect a gateway or DhanClient.

    Tries DhanClient first (from env vars), falls back to old Gateway.

    Args:
        broker: Broker name (used for fallback)

    Returns:
        Connected Gateway or DhanClient instance
    """
    client = _make_dhan_client()
    if client is not None:
        return client
    gw = Gateway(broker=broker)
    return gw
