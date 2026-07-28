from __future__ import annotations

from decimal import Decimal

from scalpr.domain.order import OrderSide, OrderState, OrderType
from scalpr.domain.tick import OHLCV
from scalpr.domain.values import ZERO
from scalpr.oms.paper_oms import PaperOms
from scalpr.simulation.fill_simulator import FillSimulator
from scalpr.strategy.strategy_port import IStrategy


class EventDrivenBacktester:
    """Historical backtest simulator executing strategies over OHLCV sequences."""

    def __init__(self, strategy: IStrategy, paper_oms: PaperOms, brokerage_flat: Decimal = Decimal("20.00")) -> None:
        self.strategy = strategy
        self.paper_oms = paper_oms
        self.brokerage_flat = brokerage_flat
        self.total_transaction_costs = ZERO
        self.fill_simulator = FillSimulator()

    def run(self, symbol: str, bars: list[OHLCV]) -> None:
        """Run backtest. Feeds bars to strategy sequentially."""
        for bar in bars:
            # 1. Update mark price on paper OMS
            self.paper_oms.set_last_price(symbol, bar.close)

            # 2. Check pending limit orders fill (simplified simulation)
            for order_id, order in list(self.paper_oms.orders_dict.items()):
                if order.state == OrderState.PENDING and order.order_type == OrderType.LIMIT:
                    fill_price = self.fill_simulator.check_limit_fill(order, bar)
                    if fill_price:
                        # Perform execute
                        self.paper_oms.place_order(order)
                        self._charge_fees(order.quantity, fill_price, order.side)

            # 3. Feed bar to strategy
            self.strategy.on_bar(bar)

    def _charge_fees(self, quantity: int, price: Decimal, side: OrderSide) -> None:
        """Charge brokerage + Securities Transaction Tax (STT) at Indian market rates."""
        turnover = price * Decimal(quantity)

        # Indian Brokerage: Flat 20 INR
        brokerage = self.brokerage_flat

        # Securities Transaction Tax (STT): 0.025% on sell side for futures/options
        stt = ZERO
        if side == OrderSide.SELL:
            stt = turnover * Decimal("0.00025")

        cost = brokerage + stt
        self.total_transaction_costs += cost
        self.paper_oms.balance -= cost
