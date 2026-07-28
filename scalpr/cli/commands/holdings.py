"""Holdings commands."""

import click
from rich.console import Console
from rich.table import Table

from scalpr.cli.utils import get_gateway

console = Console()


@click.command()  # type: ignore[untyped-decorator]
@click.option("--broker", default="dhan", help="Broker name")  # type: ignore[untyped-decorator]
def holdings(broker: str) -> None:
    """View long-term delivery holdings."""
    gw = get_gateway(broker)

    try:
        holdings_list = gw.holdings()

        if not holdings_list:
            console.print("No holdings found", style="yellow")
            return

        table = Table(title="Holdings")
        table.add_column("Symbol", style="cyan")
        table.add_column("Exchange", style="white")
        table.add_column("Quantity", style="white")
        table.add_column("Avg Price", style="white")
        table.add_column("Current Price", style="white")
        table.add_column("P&L", style="green")

        for h in holdings_list:
            pnl_style = "green" if h.pnl >= 0 else "red"
            table.add_row(
                h.symbol,
                h.exchange,
                str(h.quantity),
                f"₹{h.average_price}",
                f"₹{h.current_price}",
                f"₹{h.pnl}",
                style=pnl_style
            )

        console.print(table)
    finally:
        gw.disconnect()
