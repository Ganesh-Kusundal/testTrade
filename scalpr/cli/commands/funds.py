"""Funds and margin commands."""

import click
from rich.console import Console
from rich.table import Table

from scalpr.cli.utils import get_gateway

console = Console()


@click.command()  # type: ignore[untyped-decorator]
@click.option("--broker", default="dhan", help="Broker name")  # type: ignore[untyped-decorator]
def funds(broker: str) -> None:
    """View account funds and margin details."""
    gw = get_gateway(broker)

    try:
        funds_data = gw.funds()

        table = Table(title="Account Funds")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Balance", f"₹{funds_data.total_balance}")
        table.add_row("Available Margin", f"₹{funds_data.available_margin}")
        table.add_row("Used Margin", f"₹{funds_data.used_margin}")
        table.add_row("Collateral", f"₹{funds_data.collateral}")
        table.add_row("Real-time", "Yes" if funds_data.realtime else "No")

        console.print(table)
    finally:
        gw.disconnect()
