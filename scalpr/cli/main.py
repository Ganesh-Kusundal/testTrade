"""TradeX CLI main entry point.

Provides command-line interface for all trading operations.

Usage:
    tradex broker list
    tradex funds
    tradex holdings
    tradex positions
    tradex orders
    tradex trades
    tradex history TCS
    tradex quote TCS
"""

import sys

import click
from dotenv import load_dotenv
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="tradex")
def cli():
    """TradeX - Terminal Trading Interface.

    A powerful CLI for interacting with broker APIs, viewing market data,
    managing orders, and monitoring portfolios.
    """
    # Auto-load .env for all commands
    load_dotenv()


# Register subcommands
from scalpr.cli.commands import (  # noqa: E402 — registration must follow group definition
    broker,
    funds,
    history,
    holdings,
    orders,
    positions,
    quote,
    stream,
    trades,
)

cli.add_command(broker.broker)
cli.add_command(funds.funds)
cli.add_command(holdings.holdings)
cli.add_command(positions.positions)
cli.add_command(orders.orders)
cli.add_command(trades.trades)
cli.add_command(history.history)
cli.add_command(quote.quote)
cli.add_command(stream.stream)


def main():
    """CLI entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()
