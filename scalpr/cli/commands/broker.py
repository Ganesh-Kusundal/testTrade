"""Broker management commands."""

import click
from rich.console import Console
from rich.table import Table

from scalpr.brokers import BrokerRegistry

console = Console()


@click.group()  # type: ignore[untyped-decorator]
def broker() -> None:
    """Broker management commands."""
    pass


@broker.command("list")  # type: ignore[untyped-decorator]
def list_brokers() -> None:
    """List available brokers and their status."""
    brokers = BrokerRegistry.list_brokers()

    table = Table(title="Available Brokers")
    table.add_column("Broker", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Description", style="white")

    for name in brokers:
        table.add_row(
            name,
            "✅ Available",
            f"{name.title()} broker gateway"
        )

    console.print(table)
