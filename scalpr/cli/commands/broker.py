"""Broker management commands."""


import click
from rich.console import Console
from rich.table import Table

from scalpr.cli.utils import _make_dhan_client

console = Console()


@click.group()
def broker() -> None:
    """Broker management commands."""
    pass


@broker.command("list")
def list_brokers() -> None:
    """List available brokers and their status."""
    client = _make_dhan_client()

    table = Table(title="Available Brokers")
    table.add_column("Broker", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Description", style="white")

    if client is not None:
        try:
            positions = client.get_positions()
            funds = client.get_funds()
            bal = funds.get("balance", funds.get("total", funds.get("data", {})))
            table.add_row(
                "dhan",
                "✅ Connected",
                f"DhanClient: {len(positions)} positions, Funds: ₹{bal}",
            )
        except Exception as e:
            table.add_row("dhan", "⚠ Connected", f"DhanClient adapter ({e})")
        finally:
            client.stop()
    else:
        for name in ["dhan"]:
            table.add_row(
                name,
                "✅ Available",
                f"{name.title()} broker gateway",
            )

    console.print(table)
