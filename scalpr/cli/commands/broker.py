"""Broker management commands."""

import click
from rich.console import Console
from rich.table import Table

from scalpr.brokers import BrokerRegistry

console = Console()


@click.group()
def broker():
    """Broker management commands."""
    pass


@broker.command("list")
def list_brokers():
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
