"""Shared CLI utilities."""

from rich.console import Console

from scalpr.brokers import Gateway

console = Console()


def get_gateway(broker: str = "dhan") -> Gateway:
    """Create and connect gateway.

    Args:
        broker: Broker name

    Returns:
        Connected Gateway instance
    """
    try:
        gw = Gateway(broker=broker)
        return gw
    except Exception as e:
        console.print(f"❌ Failed to connect to {broker}: {e}", style="bold red")
        raise
