"""Trades commands."""

import click
from rich.console import Console
from rich.table import Table

from scalpr.cli.utils import get_gateway

console = Console()


@click.command()  # type: ignore[untyped-decorator]
@click.option("--broker", default="dhan", help="Broker name")  # type: ignore[untyped-decorator]
def trades(broker: str) -> None:
    """View today's executed trades."""
    gw = get_gateway(broker)

    try:
        trades_list = gw.trades()

        if not trades_list:
            console.print("No trades today", style="yellow")
            return

        table = Table(title="Trades")
        table.add_column("Trade ID", style="cyan")
        table.add_column("Symbol", style="white")
        table.add_column("Side", style="white")
        table.add_column("Qty", style="white")
        table.add_column("Price", style="white")

        for trade in trades_list:
            table.add_row(
                trade.trade_id[:12] + "...",
                trade.symbol,
                trade.side.value,
                str(trade.quantity),
                f"₹{trade.price}"
            )

        console.print(table)
        console.print(f"\nTotal: {len(trades_list)} trades")
    finally:
        gw.disconnect()
