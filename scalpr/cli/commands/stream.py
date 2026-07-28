"""Stream command - Live market data streaming with Rich display."""

import time
from datetime import datetime

import click
from rich.console import Console
from rich.live import Live
from rich.table import Table

from scalpr.brokers import Gateway
from scalpr.domain.tick import Tick

console = Console()


@click.command()
@click.argument("symbols", nargs=-1, required=True)
@click.option("--exchange", default="NSE", help="Exchange code")
@click.option("--broker", default="dhan", help="Broker name")
@click.option("--duration", default=30, help="Stream duration in seconds (0 for infinite)")
def stream(symbols: tuple[str], exchange: str, broker: str, duration: int):
    """Stream live market data for symbols.

    Examples:
        tradex stream TCS
        tradex stream TCS RELIANCE INFY
        tradex stream TCS --duration 60
    """
    gw = Gateway(broker=broker)

    # Track tick data
    tick_data = {}
    tick_count = 0
    start_time = time.time()

    def on_tick(tick: Tick) -> None:
        """Update tick data for display."""
        nonlocal tick_count
        tick_count += 1

        symbol = tick.symbol
        tick_data[symbol] = {
            'ltp': tick.last_traded_price,
            'bid': tick.bid_price if hasattr(tick, 'bid_price') else 0,
            'ask': tick.ask_price if hasattr(tick, 'ask_price') else 0,
            'volume': tick.volume if hasattr(tick, 'volume') else 0,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
        }

    def generate_table() -> Table:
        """Generate Rich table with current tick data."""
        elapsed = time.time() - start_time
        max(0, duration - elapsed) if duration > 0 else float('inf')

        table = Table(
            title=f"Live Stream ({', '.join(symbols)}) - {elapsed:.0f}s elapsed",
            show_header=True,
            header_style="bold cyan"
        )

        table.add_column("Symbol", style="cyan")
        table.add_column("LTP", style="green")
        table.add_column("Bid", style="white")
        table.add_column("Ask", style="white")
        table.add_column("Volume", style="white")
        table.add_column("Last Update", style="white")

        for symbol in symbols:
            if symbol in tick_data:
                data = tick_data[symbol]
                table.add_row(
                    symbol,
                    f"₹{data['ltp']}",
                    f"₹{data['bid']}",
                    f"₹{data['ask']}",
                    f"{data['volume']:,}",
                    data['timestamp']
                )
            else:
                table.add_row(
                    symbol,
                    "Waiting...",
                    "-",
                    "-",
                    "-",
                    "-"
                )

        return table

    try:
        # Subscribe to streaming
        console.print(f"\n📡 Subscribing to {', '.join(symbols)}...", style="bold cyan")
        gw.stream(list(symbols), exchange=exchange, callback=on_tick)
        console.print("✅ Streaming started\n", style="bold green")

        # Display live updates
        if duration > 0:
            console.print(f"⏱️  Stream duration: {duration} seconds\n", style="yellow")
        else:
            console.print("⏱️  Stream duration: infinite (Ctrl+C to stop)\n", style="yellow")

        with Live(generate_table(), refresh_per_second=2, screen=True) as live:
            try:
                while True:
                    elapsed = time.time() - start_time

                    # Check duration limit
                    if duration > 0 and elapsed >= duration:
                        break

                    live.update(generate_table())
                    time.sleep(0.5)

            except KeyboardInterrupt:
                console.print("\n⚠️  Stream interrupted by user", style="yellow")

        # Summary
        elapsed = time.time() - start_time
        console.print("\n✅ Stream complete", style="bold green")
        console.print(f"   Duration: {elapsed:.1f} seconds")
        console.print(f"   Total ticks: {tick_count}")
        if elapsed > 0:
            console.print(f"   Rate: {tick_count/elapsed:.2f} ticks/sec")

    except Exception as e:
        console.print(f"\n❌ Streaming error: {e}", style="bold red")
        raise
    finally:
        gw.stop_stream()
        gw.disconnect()
