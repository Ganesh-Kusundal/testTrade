"""Broker adapter contract suite (plan Task 8.4).

One suite, parametrized over [DhanGateway(faked connection), SimulatedGateway],
asserting IBrokerGateway semantics every adapter must honour:

- place_order returns a domain Fill (Decimal price) matching the request
- get_positions/get_margins speak the domain vocabulary
- connect/disconnect/is_connected lifecycle is truthful
- rate-limit exhaustion surfaces as the broker-agnostic RateLimitError
  (never a silent hang, never retry-in-line)
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from scalpr.brokers.contracts import Funds
from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.brokers.dhan.exceptions import RateLimitError as DhanRateLimitError
from scalpr.brokers.dhan.gateway import DhanGateway
from scalpr.brokers.errors import RateLimitError
from scalpr.brokers.rate_limit import limiter_from_table
from scalpr.domain.clock import SimulatedClock
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position
from scalpr.simulation.simulated_gateway import SimulatedGateway

pytestmark = pytest.mark.contract

T0 = datetime(2026, 1, 5, 9, 15, tzinfo=timezone.utc)


def _order(qty: int = 10) -> Order:
    return Order(
        order_id="", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=qty,
        state=OrderState.PENDING,
    )


# ── Dhan harness: gateway facade over a faked DhanConnection ────────────────

class _FakeOrdersAdapter:
    def __init__(self, throttled: bool = False) -> None:
        self.throttled = throttled

    def place_order(self, order: Order) -> Fill:
        if self.throttled:
            raise DhanRateLimitError("Rate limit budget exhausted (orders bucket)")
        return Fill(
            fill_id="DHAN-FILL-1", order_id="DHAN-ORD-1", symbol=order.symbol,
            side=order.side, quantity=order.quantity, price=Decimal("2500.05"),
            timestamp=T0, exchange="NSE",
        )


class _FakePortfolioAdapter:
    def get_positions(self) -> list[Position]:
        return [Position(symbol="RELIANCE", exchange=Exchange.NSE, quantity=10,
                         avg_price=Decimal("2500.05"), ltp=Decimal("2500.05"))]

    def get_fund_limits(self) -> Funds:
        return Funds(
            available_margin=Decimal("900000"),
            used_margin=Decimal("100000"),
            total_balance=Decimal("1000000"),
            collateral=Decimal("0"),
            realtime=True,
        )


class _FakeConnection:
    """Stateful stand-in for DhanConnection — no HTTP, truthful lifecycle."""

    def __init__(self, throttled: bool = False) -> None:
        self._connected = False
        self.orders = _FakeOrdersAdapter(throttled=throttled)
        self.portfolio = _FakePortfolioAdapter()

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected


def _dhan_gateway(throttled: bool = False) -> DhanGateway:
    gateway = DhanGateway.__new__(DhanGateway)  # skip real DhanConnection ctor
    gateway._connection = _FakeConnection(throttled=throttled)
    return gateway


def _simulated_gateway(throttled: bool = False) -> SimulatedGateway:
    limiter = None
    if throttled:
        limiter = limiter_from_table({
            "orders": {"sustained_rps": 0.001, "burst_rps": 1.0,
                       "min_interval_ms": 0, "cooldown_on_429_s": 0},
        })
    gateway = SimulatedGateway(
        starting_capital=Decimal("1000000"),
        clock=SimulatedClock(T0),
        limiter=limiter,
    )
    gateway.set_ltp("RELIANCE", Decimal("2500.00"))
    if throttled:
        # burn the single burst token so the next order hits the wall
        import scalpr.simulation.simulated_gateway as sg
        sg._ACQUIRE_TIMEOUT_S = 0.01
        gateway.connect()
        gateway.place_order(_order(qty=1))
        gateway.disconnect()
    return gateway


@pytest.fixture(autouse=True)
def _restore_sim_timeout():
    import scalpr.simulation.simulated_gateway as sg
    original = sg._ACQUIRE_TIMEOUT_S
    yield
    sg._ACQUIRE_TIMEOUT_S = original


FACTORIES = {
    "dhan": _dhan_gateway,
    "simulated": _simulated_gateway,
}


@pytest.fixture(params=sorted(FACTORIES))
def make_gateway(request):
    return FACTORIES[request.param]


class TestGatewayContract:
    def test_implements_port(self, make_gateway):
        assert isinstance(make_gateway(), IBrokerGateway)

    def test_lifecycle_is_truthful(self, make_gateway):
        gateway = make_gateway()
        gateway.connect()
        assert gateway.is_connected() is True
        gateway.disconnect()
        assert gateway.is_connected() is False

    def test_place_order_returns_matching_fill(self, make_gateway):
        gateway = make_gateway()
        gateway.connect()
        fill = gateway.place_order(_order(qty=10))
        assert isinstance(fill, Fill)
        assert fill.symbol == "RELIANCE"
        assert fill.side is OrderSide.BUY
        assert fill.quantity == 10
        assert isinstance(fill.price, Decimal)
        assert fill.order_id  # broker assigned a real id

    def test_positions_speak_domain_vocabulary(self, make_gateway):
        gateway = make_gateway()
        gateway.connect()
        gateway.place_order(_order(qty=10))
        positions = gateway.get_positions()
        assert all(isinstance(p, Position) for p in positions)

    def test_margins_are_decimal(self, make_gateway):
        gateway = make_gateway()
        gateway.connect()
        margins = gateway.get_margins()
        assert isinstance(margins.total_balance, Decimal)
        assert isinstance(margins.available_margin, Decimal)

    def test_throttle_surfaces_as_shared_rate_limit_error(self, make_gateway):
        """429/limiter exhaustion → RateLimitError fast — never a hang."""
        factory = make_gateway
        gateway = factory(throttled=True)
        gateway.connect()
        with pytest.raises(RateLimitError):
            gateway.place_order(_order(qty=1))
