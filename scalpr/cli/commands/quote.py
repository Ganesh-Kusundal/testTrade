"""Quote commands."""

import click
from rich.console import Console
from rich.table import Table

from scalpr.cli.utils import get_gateway

console = Console()


@click.command()  # type: ignore[untyped-decorator]
@click.argument("symbol")  # type: ignore[untyped-decorator]
@click.option("--exchange", default="NSE", help="Exchange code")  # type: ignore[untyped-decorator]
@click.option("--broker", default="dhan", help="Broker name")  # type: ignore[untyped-decorator]
def quote(symbol: str, exchange: str, broker: str) -> None:
    """View live market quote for a symbol."""
    gw = get_gateway(broker)

    try:
        quote_data = gw.quote(symbol, exchange=exchange)

        table = Table(title=f"Quote: {symbol}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("LTP", f"₹{quote_data.ltp}")
        table.add_row("Open", f"₹{quote_data.open}")
        table.add_row("High", f"₹{quote_data.high}")
        table.add_row("Low", f"₹{quote_data.low}")
        table.add_row("Close", f"₹{quote_data.close}")
        table.add_row("Volume", f"{quote_data.volume:,}")
        table.add_row("Change", f"₹{quote_data.change}")
        table.add_row("Change %", f"{quote_data.change_percent}%")

        console.print(table)
    finally:
        gw.disconnect()
