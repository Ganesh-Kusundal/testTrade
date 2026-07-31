"""SimulatedGateway unit tests — deterministic paper broker semantics."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from scalpr.domain.clock import SimulatedClock
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import PositionSide
from scalpr.simulation.simulated_gateway import SimulatedGateway

T0 = datetime(2026, 1, 5, 9, 15, tzinfo=timezone.utc)


def _gateway(**overrides) -> SimulatedGateway:
    kwargs = {
        "starting_capital": Decimal("1000000"),
        "clock": SimulatedClock(T0),
    }
    kwargs.update(overrides)
    gw = SimulatedGateway(**kwargs)
    gw.connect()
    gw.set_ltp("RELIANCE", Decimal("2500.00"))
    return gw


def _order(side=OrderSide.BUY, order_type=OrderType.MARKET, qty=10,
           price=Decimal("0")) -> Order:
    return Order(
        order_id="", symbol="RELIANCE", exchange=Exchange.NSE,
        side=side, order_type=order_type, quantity=qty, price=price,
        state=OrderState.PENDING,
    )


class TestConstruction:
    def test_capital_must_be_decimal(self):
        with pytest.raises(TypeError, match="never float"):
            SimulatedGateway(starting_capital=1000000.0)

    def test_capital_must_be_positive(self):
        with pytest.raises(ValueError, match="positive"):
            SimulatedGateway(starting_capital=Decimal("0"))

    def test_capital_is_mandatory(self):
        with pytest.raises(TypeError):
            SimulatedGateway()  # fail-closed: no hidden capital defaults

    def test_lifecycle(self):
        gw = SimulatedGateway(starting_capital=Decimal("1"))
        assert not gw.is_connected()
        gw.connect()
        assert gw.is_connected()
        gw.disconnect()
        assert not gw.is_connected()


class TestOrderExecution:
    def test_market_buy_fills_with_slippage(self):
        gw = _gateway()
        fill = gw.place_order(_order())
        # default FillSimulator: 1 tick (0.05) adverse slippage on buys
        assert fill.price == Decimal("2500.05")
        assert fill.quantity == 10
        assert fill.timestamp == T0  # injected clock, not wall-clock

    def test_market_sell_slippage_is_adverse(self):
        gw = _gateway()
        fill = gw.place_order(_order(side=OrderSide.SELL))
        assert fill.price == Decimal("2499.95")

    def test_limit_order_fills_at_limit_price(self):
        gw = _gateway()
        fill = gw.place_order(
            _order(order_type=OrderType.LIMIT, price=Decimal("2499.00"))
        )
        assert fill.price == Decimal("2499.00")

    def test_market_order_without_ltp_is_rejected(self):
        gw = SimulatedGateway(starting_capital=Decimal("1000"), clock=SimulatedClock(T0))
        gw.connect()
        with pytest.raises(ValueError, match="No simulated LTP"):
            gw.place_order(_order())

    def test_ids_are_deterministic(self):
        fills_a = [_gateway().place_order(_order()).fill_id for _ in range(1)]
        fills_b = [_gateway().place_order(_order()).fill_id for _ in range(1)]
        assert fills_a == fills_b == ["SIM-FILL-2"]  # SIM-ORD-1 then SIM-FILL-2

    def test_order_book_reflects_fill(self):
        gw = _gateway()
        fill = gw.place_order(_order())
        order = gw.get_order_status(fill.order_id)
        assert order.state is OrderState.FILLED
        assert order.filled_quantity == 10
        assert order.avg_price == fill.price
        assert gw.get_orders() == [order]
        assert gw.get_tradebook() == [fill]

    def test_modify_and_cancel_return_false_after_instant_fill(self):
        gw = _gateway()
        fill = gw.place_order(_order())
        assert gw.modify_order(fill.order_id, Decimal("2400"), 5) is False
        assert gw.cancel_order(fill.order_id) is False


class TestPositionsAndFunds:
    def test_position_tracks_fills(self):
        gw = _gateway()
        gw.place_order(_order(qty=10))
        [position] = gw.get_positions()
        assert position.quantity == 10
        assert position.position_side is PositionSide.LONG
        assert position.avg_price == Decimal("2500.05")

    def test_round_trip_realises_pnl_in_margins(self):
        gw = _gateway()
        gw.place_order(_order(qty=10))
        gw.set_ltp("RELIANCE", Decimal("2510.00"))
        gw.place_order(_order(side=OrderSide.SELL, qty=10))
        assert gw.get_positions() == []  # flat
        margins = gw.get_margins()
        # bought @2500.05, sold @2509.95 → +9.90 * 10 = 99.00
        assert margins.total_balance == Decimal("1000000") + Decimal("99.00")
        assert isinstance(margins.total_balance, Decimal)
        assert margins.realtime is False

    def test_square_off_all_flattens(self):
        gw = _gateway()
        gw.place_order(_order(qty=10))
        fills = gw.square_off_all()
        assert len(fills) == 1
        assert fills[0].side is OrderSide.SELL
        assert fills[0].quantity == 10
        assert gw.get_positions() == []

    def test_no_holdings_in_intraday_sim(self):
        assert _gateway().get_holdings() == []


class TestMarketData:
    def test_ltp_and_quote(self):
        gw = _gateway()
        assert gw.get_ltp("RELIANCE") == Decimal("2500.00")
        quote = gw.get_quote("RELIANCE")
        assert quote["ltp"] == Decimal("2500.00")

    def test_ohlcv_is_empty(self):
        gw = _gateway()
        assert gw.get_ohlcv("RELIANCE", "NSE", "1m", date(2026, 1, 1), date(2026, 1, 5)) == []


class TestRateLimiting:
    def test_paper_limits_never_block_a_burst(self):
        gw = _gateway()
        for _ in range(50):
            gw.place_order(_order(qty=1))
        assert len(gw.get_tradebook()) == 50
