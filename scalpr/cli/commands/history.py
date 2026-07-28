"""Historical data commands."""

import click
from rich.console import Console
from rich.table import Table

from scalpr.cli.utils import get_gateway

console = Console()


@click.command()  # type: ignore[untyped-decorator]
@click.argument("symbol")  # type: ignore[untyped-decorator]
@click.option("--exchange", default="NSE", help="Exchange code")  # type: ignore[untyped-decorator]
@click.option("--timeframe", default="1m", help="Candle timeframe (1m, 5m, 15m, 1H, 1D)")  # type: ignore[untyped-decorator]
@click.option("--days", default=30, help="Lookback days")  # type: ignore[untyped-decorator]
@click.option("--broker", default="dhan", help="Broker name")  # type: ignore[untyped-decorator]
def history(symbol: str, exchange: str, timeframe: str, days: int, broker: str) -> None:
    """View historical OHLCV data for a symbol."""
    gw = get_gateway(broker)

    try:
        df = gw.history(symbol, exchange=exchange, timeframe=timeframe, lookback_days=days)

        if df.empty:
            console.print(f"No historical data for {symbol}", style="yellow")
            return

        table = Table(title=f"History: {symbol} ({timeframe}, {days} days)")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Open", style="white")
        table.add_column("High", style="white")
        table.add_column("Low", style="white")
        table.add_column("Close", style="white")
        table.add_column("Volume", style="white")

        # Show last 20 candles
        for _, row in df.tail(20).iterrows():
            table.add_row(
                str(row['timestamp']),
                f"{row['open']:.2f}",
                f"{row['high']:.2f}",
                f"{row['low']:.2f}",
                f"{row['close']:.2f}",
                f"{row['volume']:.0f}"
            )

        console.print(table)
        console.print(f"\nTotal candles: {len(df)}")
    finally:
        gw.disconnect()
