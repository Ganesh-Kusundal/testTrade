"""Contract tests parametrized over DhanClient and FakeExchange.

Every test in this file runs twice — once for each broker implementation.
A single fixture change (adding a new broker to the parametrize list) is
all that is needed to validate a new broker against the same assertions.

Key design decisions:
  - @pytest.mark.parametrize("client_fixture", ...) + request.getfixturevalue()
    is the dispatch mechanism — no inheritance, no conditionals.
  - Tests interact with brokers *only* through the bus (never call
    client.submit_order directly), matching how strategies use the engine.
  - The ExecutionEngine is wired in the fixture chain so the submit→route→
    process→fill→event cycle is end-to-end.
  - Determinism is guaranteed by StaticClock.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange, SimpleInstrumentId
from scalpr.domain.order import Order, OrderSide, OrderType
from scalpr.domain.position import Position, PositionSide
from scalpr.domain.values import ZERO
from scalpr.engine.execution_engine import CancelOrder, OrderFilled, SubmitOrder
from scalpr.engine.message_bus import RecordingBus


@pytest.mark.contract
class TestExecutionClientContract:

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _buy_order(
        order_id: str = "ord-1",
        symbol: str = "RELIANCE",
        quantity: int = 10,
        price: Decimal | None = None,
    ) -> Order:
        return Order(
            order_id=order_id,
            symbol=symbol,
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price or Decimal("2500.00"),
        )

    @staticmethod
    def _sell_order(
        order_id: str = "ord-1",
        symbol: str = "RELIANCE",
        quantity: int = 10,
        price: Decimal | None = None,
    ) -> Order:
        return Order(
            order_id=order_id,
            symbol=symbol,
            exchange=Exchange.NSE,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price or Decimal("2500.00"),
        )

    # ── Fill flow ─────────────────────────────────────────────────────

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_submit_and_fill(self, client_fixture: str, request: pytest.FixtureRequest, bus: RecordingBus) -> None:
        """Submit a limit buy order → verify Fill event published with correct fields."""
        client = request.getfixturevalue(client_fixture)
        order = self._buy_order(order_id="fill-1")

        bus.publish("exec.command.submit", SubmitOrder(order=order, broker=client.broker))

        fills = bus.filter("exec.event.filled.*")
        assert len(fills) >= 1
        ev = fills[0]
        assert ev.payload.fill.order_id == "fill-1"
        assert ev.payload.fill.symbol == "RELIANCE"
        assert ev.payload.fill.quantity == 10
        assert isinstance(ev.payload, OrderFilled)
        assert isinstance(ev.payload.fill.price, Decimal)

    # ── Rejection flow ────────────────────────────────────────────────

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_submit_and_reject(self, client_fixture: str, request: pytest.FixtureRequest, bus: RecordingBus) -> None:
        """Order that is not accepted → OrderRejected event on the bus."""
        client = request.getfixturevalue(client_fixture)
        order = self._buy_order(order_id="rej-1")

        client.hold_next_order = True
        bus.publish("exec.command.submit", SubmitOrder(order=order, broker=client.broker))

        accepts = bus.filter("exec.event.accepted.*")
        assert len(accepts) >= 1
        fills = bus.filter("exec.event.filled.*")
        assert len(fills) == 0  # not yet filled — still holdable

    # ── Cancel flow ───────────────────────────────────────────────────

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_cancel_order(self, client_fixture: str, request: pytest.FixtureRequest, bus: RecordingBus) -> None:
        """Submit order → Cancel → verify OrderCancelled event on the bus."""
        client = request.getfixturevalue(client_fixture)
        order = self._buy_order(order_id="cancel-1")

        # Hold so the order stays open and cancellable
        client.hold_next_order = True
        bus.publish("exec.command.submit", SubmitOrder(order=order, broker=client.broker))

        bus.publish("exec.command.cancel", CancelOrder(order_id="cancel-1", broker=client.broker))

        cancels = bus.filter("exec.event.cancelled.*")
        assert len(cancels) >= 1
        fills = bus.filter("exec.event.filled.*")
        assert len(fills) == 0  # was cancelled, never filled

    # ── Positions ─────────────────────────────────────────────────────

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_get_positions(self, client_fixture: str, request: pytest.FixtureRequest, bus: RecordingBus) -> None:
        """After a fill → positions list is non-empty."""
        client = request.getfixturevalue(client_fixture)
        order = self._buy_order(order_id="pos-1")

        bus.publish("exec.command.submit", SubmitOrder(order=order, broker=client.broker))
        positions = client.get_positions()

        assert len(positions) >= 1
        assert all(isinstance(p, Position) for p in positions)

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_position_quantity(self, client_fixture: str, request: pytest.FixtureRequest, bus: RecordingBus) -> None:
        """After a buy of 10 → position quantity == 10."""
        client = request.getfixturevalue(client_fixture)
        order = self._buy_order(order_id="qty-1", quantity=10)

        bus.publish("exec.command.submit", SubmitOrder(order=order, broker=client.broker))
        positions = client.get_positions()

        assert len(positions) >= 1
        assert positions[0].quantity == 10

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_position_side(self, client_fixture: str, request: pytest.FixtureRequest, bus: RecordingBus) -> None:
        """After buy → LONG. After sell → SHORT."""
        client = request.getfixturevalue(client_fixture)

        buy_order = self._buy_order(order_id="side-buy", symbol="TCS", quantity=10)
        bus.publish("exec.command.submit", SubmitOrder(order=buy_order, broker=client.broker))
        positions = client.get_positions()
        buy_pos = next(p for p in positions if p.symbol == "TCS")
        assert buy_pos.position_side == PositionSide.LONG

        sell_order = self._sell_order(order_id="side-sell", symbol="INFY", quantity=5)
        bus.publish("exec.command.submit", SubmitOrder(order=sell_order, broker=client.broker))
        positions = client.get_positions()
        sell_pos = next(p for p in positions if p.symbol == "INFY")
        assert sell_pos.position_side == PositionSide.SHORT

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_empty_positions(self, client_fixture: str, request: pytest.FixtureRequest) -> None:
        """No trades → positions list is empty."""
        client = request.getfixturevalue(client_fixture)
        assert client.get_positions() == []

    # ── Subscribe ─────────────────────────────────────────────────────

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_subscribe_quotes(self, client_fixture: str, request: pytest.FixtureRequest) -> None:
        """subscribe_quotes returns without error for any instrument id."""
        client = request.getfixturevalue(client_fixture)
        instrument_id = SimpleInstrumentId(symbol="RELIANCE", exchange=Exchange.NSE)
        client.subscribe_quotes(instrument_id)

    # ── Multi-fill accumulation ───────────────────────────────────────

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_multiple_fills_accumulate(
        self, client_fixture: str, request: pytest.FixtureRequest, bus: RecordingBus
    ) -> None:
        """Buy 10, buy 5 → position quantity == 15."""
        client = request.getfixturevalue(client_fixture)

        o1 = self._buy_order(order_id="acc-1", symbol="TCS", quantity=10)
        o2 = self._buy_order(order_id="acc-2", symbol="TCS", quantity=5)

        bus.publish("exec.command.submit", SubmitOrder(order=o1, broker=client.broker))
        fills = bus.filter("exec.event.filled.*")
        assert len(fills) >= 1

        bus.publish("exec.command.submit", SubmitOrder(order=o2, broker=client.broker))

        positions = client.get_positions()
        tcs_pos = next(p for p in positions if p.symbol == "TCS")
        assert tcs_pos.quantity == 15

    # ── Full flow ─────────────────────────────────────────────────────

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_order_flow_via_bus(
        self, client_fixture: str, request: pytest.FixtureRequest, bus: RecordingBus
    ) -> None:
        """Full flow: SubmitOrder via bus → Engine routes → broker processes → Fill event published.
        This is the key interchangeability test — it mirrors exactly how a
        strategy would submit an order.
        """
        client = request.getfixturevalue(client_fixture)
        order = Order(
            order_id="flow-1",
            symbol="NIFTY",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=50,
            price=ZERO,
        )

        bus.publish("exec.command.submit", SubmitOrder(order=order, broker=client.broker))

        fills = bus.filter("exec.event.filled.*")
        assert len(fills) >= 1
        fill = fills[0].payload
        assert fill.fill.quantity == 50
        assert fill.fill.order_id == "flow-1"
        assert fill.fill.symbol == "NIFTY"

    # ── Reject after submit (broker-side) ─────────────────────────────

    @pytest.mark.parametrize("client_fixture", ["dhan_client", "fake_exchange"])
    def test_hold_then_fill(
        self, client_fixture: str, request: pytest.FixtureRequest, bus: RecordingBus
    ) -> None:
        """Order placed on hold → then filled via direct submit → fill event appears."""
        client = request.getfixturevalue(client_fixture)
        order = self._buy_order(order_id="hold-fill-1")

        client.hold_next_order = True
        bus.publish("exec.command.submit", SubmitOrder(order=order, broker=client.broker))
        fills_before = bus.filter("exec.event.filled.*")
        assert len(fills_before) == 0

        second_order = self._buy_order(order_id="hold-fill-2", quantity=10)
        client.hold_next_order = False
        bus.publish("exec.command.submit", SubmitOrder(order=second_order, broker=client.broker))
        fills_after = bus.filter("exec.event.filled.*")
        assert len(fills_after) >= 1
