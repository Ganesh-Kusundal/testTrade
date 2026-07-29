"""Stream command - Live market data streaming with Rich display."""

import os
import time
from datetime import datetime
from typing import Any

import click
from rich.console import Console
from rich.live import Live
from rich.table import Table

from scalpr.brokers import Gateway
from scalpr.domain.instrument import Exchange, SimpleInstrumentId
from scalpr.domain.tick import Tick
from scalpr.engine.clock import LiveClock
from scalpr.engine.message_bus import MessageBus

console = Console()


def _try_dhan_stream(
    symbols: tuple[str, ...],
    exchange: str,
    duration: int,
) -> bool:
    """Try to stream via DhanClient. Returns True if successful, False to fall back."""
    client_id = os.environ.get("DHAN_CLIENT_ID", "")
    access_token = os.environ.get("DHAN_ACCESS_TOKEN", "")
    totp_secret = os.environ.get("DHAN_TOTP_SECRET", "")
    if not (client_id and access_token and totp_secret):
        return False

    try:
        from scalpr.adapters.dhan.client import DhanClient

        bus = MessageBus()
        clock = LiveClock()
        config = {
            "client_id": client_id,
            "access_token": access_token,
            "totp_secret": totp_secret,
            "csv_path": os.environ.get("DHAN_INSTRUMENT_CSV", "instrument.csv"),
        }
        client = DhanClient(bus, clock, config)
        client.start()
    except Exception as e:
        console.print(f"  ⚠ DhanClient init failed: {e}", style="yellow")
        return False

    tick_data: dict[str, dict[str, Any]] = {}
    tick_count = 0
    start_time = time.time()

    def on_tick(tick: Tick) -> None:
        nonlocal tick_count
        tick_count += 1
        tick_data[tick.symbol] = {
            "ltp": float(tick.ltp),
            "bid": float(tick.bid) if hasattr(tick, "bid") else 0,
            "ask": float(tick.ask) if hasattr(tick, "ask") else 0,
            "volume": tick.cumulative_volume if hasattr(tick, "cumulative_volume") else 0,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

    bus.subscribe("market.quote.dhan", on_tick)

    try:
        exchange_enum = Exchange[exchange.upper()]
    except KeyError:
        console.print(f"❌ Invalid exchange: {exchange}", style="bold red")
        client.stop()
        return True

    for sym in symbols:
        try:
            inst_id = SimpleInstrumentId(symbol=sym.upper(), exchange=exchange_enum)
            client.subscribe_quotes(inst_id)
        except Exception as e:
            console.print(f"  ⚠ Could not subscribe to {sym}: {e}", style="yellow")

    console.print(f"\n📡 Subscribing to {', '.join(symbols)}...", style="bold cyan")
    console.print("✅ Streaming started (DhanClient)\n", style="bold green")

    _run_display_loop(tick_data, symbols, duration, start_time, tick_count)
    client.stop()
    return True


def _run_display_loop(
    tick_data: dict[str, dict[str, Any]],
    symbols: tuple[str, ...],
    duration: int,
    start_time: float,
    tick_count: int,
) -> None:
    """Run the live display table loop."""

    def generate_table() -> Table:
        elapsed = time.time() - start_time
        table = Table(
            title=f"Live Stream ({', '.join(symbols)}) - {elapsed:.0f}s elapsed",
            show_header=True,
            header_style="bold cyan",
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
                    data["timestamp"],
                )
            else:
                table.add_row(symbol, "Waiting...", "-", "-", "-", "-")
        return table

    if duration > 0:
        console.print(f"⏱️  Stream duration: {duration} seconds\n", style="yellow")
    else:
        console.print("⏱️  Stream duration: infinite (Ctrl+C to stop)\n", style="yellow")

    with Live(generate_table(), refresh_per_second=2, screen=True) as live:
        try:
            while True:
                elapsed = time.time() - start_time
                if duration > 0 and elapsed >= duration:
                    break
                live.update(generate_table())
                time.sleep(0.5)
        except KeyboardInterrupt:
            console.print("\n⚠️  Stream interrupted by user", style="yellow")

    elapsed = time.time() - start_time
    console.print("\n✅ Stream complete", style="bold green")
    console.print(f"   Duration: {elapsed:.1f} seconds")
    console.print(f"   Total ticks: {tick_count}")
    if elapsed > 0:
        console.print(f"   Rate: {tick_count/elapsed:.2f} ticks/sec")


@click.command()
@click.argument("symbols", nargs=-1, required=True)
@click.option("--exchange", default="NSE", help="Exchange code")
@click.option("--broker", default="dhan", help="Broker name")
@click.option("--duration", default=30, help="Stream duration in seconds (0 for infinite)")
def stream(symbols: tuple[str], exchange: str, broker: str, duration: int) -> None:
    """Stream live market data for symbols.

    Examples:
        tradex stream TCS
        tradex stream TCS RELIANCE INFY
        tradex stream TCS --duration 60
    """
    if _try_dhan_stream(symbols, exchange, duration):
        return

    gw = Gateway(broker=broker)

    tick_data: dict[str, dict[str, Any]] = {}
    tick_count = 0
    start_time = time.time()

    def on_tick(tick: Tick) -> None:
        nonlocal tick_count
        tick_count += 1
        tick_data[tick.symbol] = {
            "ltp": float(tick.ltp) if hasattr(tick, "ltp") else 0,
            "bid": float(tick.bid) if hasattr(tick, "bid") else 0,
            "ask": float(tick.ask) if hasattr(tick, "ask") else 0,
            "volume": tick.cumulative_volume if hasattr(tick, "cumulative_volume") else 0,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

    def generate_table() -> Table:
        elapsed = time.time() - start_time
        table = Table(
            title=f"Live Stream ({', '.join(symbols)}) - {elapsed:.0f}s elapsed",
            show_header=True,
            header_style="bold cyan",
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
                    data["timestamp"],
                )
            else:
                table.add_row(symbol, "Waiting...", "-", "-", "-", "-")
        return table

    try:
        console.print(f"\n📡 Subscribing to {', '.join(symbols)}...", style="bold cyan")
        gw.stream(list(symbols), exchange=exchange, callback=on_tick)
        console.print("✅ Streaming started\n", style="bold green")

        if duration > 0:
            console.print(f"⏱️  Stream duration: {duration} seconds\n", style="yellow")
        else:
            console.print("⏱️  Stream duration: infinite (Ctrl+C to stop)\n", style="yellow")

        with Live(generate_table(), refresh_per_second=2, screen=True) as live:
            try:
                while True:
                    elapsed = time.time() - start_time
                    if duration > 0 and elapsed >= duration:
                        break
                    live.update(generate_table())
                    time.sleep(0.5)
            except KeyboardInterrupt:
                console.print("\n⚠️  Stream interrupted by user", style="yellow")

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
