"""Positions commands."""

import click
from rich.console import Console
from rich.table import Table

from scalpr.cli.utils import get_gateway

console = Console()


@click.command()  # type: ignore[untyped-decorator]
@click.option("--broker", default="dhan", help="Broker name")  # type: ignore[untyped-decorator]
def positions(broker: str) -> None:
    """View current open positions."""
    gw = get_gateway(broker)

    try:
        positions_list = gw.positions()

        if not positions_list:
            console.print("No open positions", style="yellow")
            return

        table = Table(title="Open Positions")
        table.add_column("Symbol", style="cyan")
        table.add_column("Exchange", style="white")
        table.add_column("Quantity", style="white")
        table.add_column("Avg Price", style="white")
        table.add_column("LTP", style="white")
        table.add_column("P&L", style="green")

        for pos in positions_list:
            pnl_style = "green" if pos.unrealised_pnl >= 0 else "red"
            table.add_row(
                pos.symbol,
                pos.exchange.value if hasattr(pos.exchange, 'value') else str(pos.exchange),
                str(pos.quantity),
                f"₹{pos.avg_price}",
                f"₹{pos.ltp}",
                f"₹{pos.unrealised_pnl}",
                style=pnl_style
            )

        console.print(table)
    finally:
        gw.disconnect()
