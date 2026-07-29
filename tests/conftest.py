from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "dhan_responses"


def _load_json(filename: str) -> dict | list:
    path = FIXTURES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def dhan_quote_response() -> dict:
    """Raw Dhan /marketfeed/quote POST response."""
    return _load_json("quote_response.json")


@pytest.fixture
def dhan_order_response() -> dict:
    """Raw Dhan order placement / status response with multiple states."""
    return _load_json("order_response.json")


@pytest.fixture
def dhan_position_response() -> dict:
    """Raw Dhan position detail response with long/short/flat."""
    return _load_json("position_response.json")


@pytest.fixture
def dhan_auth_response() -> dict:
    """Raw Dhan auth token response."""
    return _load_json("auth_response.json")


@pytest.fixture
def dhan_error_response() -> dict:
    """Collection of Dhan API error responses by scenario."""
    return _load_json("error_responses.json")


@pytest.fixture
def dhan_option_chain_response() -> list[dict]:
    """Raw Dhan option chain response with greeks."""
    return _load_json("option_chain_response.json")


@pytest.fixture
def quote_nse_reliance(dhan_quote_response: dict) -> dict:
    """Single NSE equity quote dict from the response list."""
    return dhan_quote_response["data"]["NSE"][0]


@pytest.fixture
def quote_nse_nifty(dhan_quote_response: dict) -> dict:
    """Single NSE F&O quote dict from the response list."""
    return dhan_quote_response["data"]["NSE"][3]


@pytest.fixture
def quote_bse_reliance(dhan_quote_response: dict) -> dict:
    """Single BSE equity quote dict from the response list."""
    return dhan_quote_response["data"]["BSE"][0]


@pytest.fixture
def quote_mcx_gold(dhan_quote_response: dict) -> dict:
    """Single MCX commodity quote dict from the response list."""
    return dhan_quote_response["data"]["MCX"][0]


# ── Contract test fixtures ────────────────────────────────────────────

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.adapters.test_helpers.fake_exchange import FakeExchange
from scalpr.domain.fill import Fill
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position
from scalpr.domain.values import ZERO
from scalpr.engine.clock import StaticClock
from scalpr.engine.execution_engine import ExecutionEngine
from scalpr.engine.message_bus import RecordingBus


class DhanClient:
    """Test Dhan broker client wired to mocked HTTP/WS. Satisfies the
    same contract as FakeExchange for broker-interchangeability tests."""

    broker = "dhan"

    def __init__(
        self,
        bus: RecordingBus,
        clock: StaticClock,
        http: MagicMock,
        ws: MagicMock,
    ) -> None:
        self._bus = bus
        self._clock = clock
        self._http = http
        self._ws = ws
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, Position] = {}
        self.hold_next_order = False

        bus.subscribe("exec.command.submit.dhan", self._on_submit)
        bus.subscribe("exec.command.cancel.dhan", self._on_cancel)

    def _on_submit(self, cmd: object) -> None:
        order = getattr(cmd, "order", None)
        if order is not None:
            self.submit_order(order)

    def _on_cancel(self, cmd: object) -> None:
        order_id = getattr(cmd, "order_id", None) or str(cmd)
        self.cancel_order(order_id)

    def submit_order(self, order: Order) -> Fill:
        if self.hold_next_order:
            self.hold_next_order = False
            self._orders[order.order_id] = order
            self._bus.publish("exec.event.accepted", order.order_id)
            return Fill(
                fill_id=f"held_{order.order_id}",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=0,
                price=ZERO,
                timestamp=self._clock.utc_now(),
            )

        self._http.post("/orders", json={})
        ts = self._clock.utc_now()
        price = order.price
        if order.order_type in (OrderType.MARKET, OrderType.STOP_LOSS_MARKET) and price == ZERO:
            price = Decimal("100.0")

        fill = Fill(
            fill_id=f"dhan_fill_{order.order_id}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=price,
            timestamp=ts,
        )

        self._orders[order.order_id] = order

        delta = order.quantity if order.side == OrderSide.BUY else -order.quantity
        pos = self._positions.get(order.symbol)
        if pos is None:
            pos = Position(symbol=order.symbol, exchange=order.exchange)
        pos = pos.with_fill(delta, price, order.side)
        self._positions[order.symbol] = pos

        self._bus.publish("exec.event.accepted", order.order_id)
        self._bus.publish("exec.event.fill", fill)
        return fill

    def cancel_order(self, order_id: str) -> bool:
        self._http.delete(f"/orders/{order_id}")
        order = self._orders.get(order_id)
        if order is None or order.state.is_terminal:
            return False
        cancelled = order.transition_to(OrderState.CANCELLED)
        self._orders[order_id] = cancelled
        self._bus.publish("exec.event.cancelled", cancelled)
        return True

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def subscribe_quotes(self, instrument_id: object) -> None:
        self._ws.subscribe([(str(instrument_id), "quote")])


class ContractFakeExchange(FakeExchange):
    """FakeExchange augmented with get_positions() and hold/reject for contract tests."""

    broker = "fake"

    def __init__(self, bus: RecordingBus) -> None:
        self.hold_next_order = False
        super().__init__(bus)

    def submit_order(self, order: Order) -> Fill:
        if self.hold_next_order:
            self.hold_next_order = False
            self._orders[order.order_id] = order
            self._bus.publish("exec.event.accepted", order.order_id)
            return Fill(
                fill_id=f"held_{order.order_id}",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=0,
                price=ZERO,
                timestamp=datetime.now(timezone.utc),
            )
        return super().submit_order(order)

    def get_positions(self) -> list[Position]:
        with self._lock:
            return list(self._positions.values())

    def subscribe_quotes(self, instrument_id: object) -> None:
        pass


@pytest.fixture
def bus() -> RecordingBus:
    return RecordingBus()


@pytest.fixture
def clock() -> StaticClock:
    return StaticClock()


@pytest.fixture
def mock_http() -> MagicMock:
    mock = MagicMock()
    mock.post.return_value = {}
    mock.delete.return_value = {}
    return mock


@pytest.fixture
def mock_ws() -> MagicMock:
    return MagicMock()


@pytest.fixture
def engine(bus: RecordingBus, clock: StaticClock) -> ExecutionEngine:
    eng = ExecutionEngine(bus, clock)
    eng.start()
    yield eng
    eng.stop()


@pytest.fixture
def dhan_client(
    bus: RecordingBus,
    clock: StaticClock,
    mock_http: MagicMock,
    mock_ws: MagicMock,
    engine: ExecutionEngine,
) -> DhanClient:
    return DhanClient(bus, clock, mock_http, mock_ws)


@pytest.fixture
def fake_exchange(bus: RecordingBus, engine: ExecutionEngine) -> ContractFakeExchange:
    return ContractFakeExchange(bus)
