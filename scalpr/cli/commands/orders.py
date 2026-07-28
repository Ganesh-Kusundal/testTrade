"""Orders commands."""

import click
from rich.console import Console
from rich.table import Table

from scalpr.cli.utils import get_gateway

console = Console()


@click.command()
@click.option("--broker", default="dhan", help="Broker name")
def orders(broker: str):
    """View today's orders."""
    gw = get_gateway(broker)

    try:
        orders_list = gw.orders()

        if not orders_list:
            console.print("No orders today", style="yellow")
            return

        table = Table(title="Orders")
        table.add_column("Order ID", style="cyan")
        table.add_column("Symbol", style="white")
        table.add_column("Side", style="white")
        table.add_column("Type", style="white")
        table.add_column("Qty", style="white")
        table.add_column("Price", style="white")
        table.add_column("Status", style="green")

        for order in orders_list:
            table.add_row(
                order.order_id[:12] + "...",
                order.symbol,
                order.side.value,
                order.order_type.value,
                str(order.quantity),
                f"₹{order.price}",
                order.state.value
            )

        console.print(table)
        console.print(f"\nTotal: {len(orders_list)} orders")
    finally:
        gw.disconnect()
