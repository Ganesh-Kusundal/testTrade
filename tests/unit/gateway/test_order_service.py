from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.domain.contracts import BrokerClientProtocol
from scalpr.domain.instrument import Exchange, ResolvedInstrument, Segment, SimpleInstrumentId
from scalpr.domain.order import (
    Order,
    OrderRequest,
    OrderSide,
    OrderState,
    Side,
)
from scalpr.engine.clock import StaticClock
from scalpr.engine.execution_engine import CancelOrder, ModifyOrder, SubmitOrder
from scalpr.engine.message_bus import RecordingBus
from scalpr.gateway.order_service import OrderService


def make_resolved(symbol: str = "TCS") -> ResolvedInstrument:
    return ResolvedInstrument(
        instrument_id=SimpleInstrumentId(symbol=symbol, exchange=Exchange.NSE),
        security_id="112833",
        exchange=Exchange.NSE,
        segment=Segment.EQUITY,
        trading_symbol=symbol,
        wire_segment="NSE_EQ",
        lot_size=1,
        tick_size=Decimal("0.05"),
        freeze_quantity=100,
        expiry=None,
        strike=None,
        option_type=None,
    )


class TestOrderServicePlace:
    def test_place_validates_and_publishes_submit(self):
        bus = RecordingBus()
        clock = StaticClock(datetime(2024, 6, 15, 10, 30))
        client = MagicMock(spec=BrokerClientProtocol)
        client.broker = "dhan"
        client.resolve_instrument.return_value = make_resolved("TCS")

        svc = OrderService(client=client, bus=bus, clock=clock)
        req = OrderRequest(
            instrument="TCS:NSE",
            side=Side.BUY,
            quantity=10,
            price=Decimal("2500"),
        )
        order = svc.place(req)

        assert isinstance(order, Order)
        assert order.side == OrderSide.BUY
        assert order.quantity == 10
        assert order.price == Decimal("2500")
        assert order.state == OrderState.PENDING

        submits = bus.filter("exec.command.submit")
        assert len(submits) == 1
        cmd = submits[0].payload
        assert isinstance(cmd, SubmitOrder)
        assert cmd.order.order_id == order.order_id
        assert cmd.broker == "dhan"

    def test_place_without_risk_service_still_works(self):
        bus = RecordingBus()
        clock = StaticClock()
        client = MagicMock(spec=BrokerClientProtocol)
        client.broker = "dhan"
        client.resolve_instrument.return_value = make_resolved("TCS")

        svc = OrderService(client=client, bus=bus, clock=clock, risk=None)
        req = OrderRequest(instrument="TCS:NSE", side=Side.BUY, quantity=10, price=Decimal("2500"))
        order = svc.place(req)
        assert order.state == OrderState.PENDING

    def test_place_with_correlation_id_uses_it_as_order_id(self):
        bus = RecordingBus()
        clock = StaticClock()
        client = MagicMock(spec=BrokerClientProtocol)
        client.broker = "dhan"
        client.resolve_instrument.return_value = make_resolved("TCS")

        svc = OrderService(client=client, bus=bus, clock=clock)
        req = OrderRequest(
            instrument="TCS:NSE", side=Side.BUY, quantity=10,
            price=Decimal("2500"), correlation_id="my-correlation-123",
        )
        order = svc.place(req)
        assert order.order_id == "my-correlation-123"


class TestOrderServiceCancel:
    def test_cancel_publishes_cancel_command(self):
        bus = RecordingBus()
        clock = StaticClock()
        client = MagicMock(spec=BrokerClientProtocol)
        client.broker = "dhan"

        svc = OrderService(client=client, bus=bus, clock=clock)
        result = svc.cancel("ord-1")

        assert result is None
        cancels = bus.filter("exec.command.cancel")
        assert len(cancels) == 1
        cmd = cancels[0].payload
        assert isinstance(cmd, CancelOrder)
        assert cmd.order_id == "ord-1"
        assert cmd.broker == "dhan"


class TestOrderServiceModify:
    def test_modify_publishes_modify_command(self):
        bus = RecordingBus()
        clock = StaticClock()
        client = MagicMock(spec=BrokerClientProtocol)
        client.broker = "dhan"

        svc = OrderService(client=client, bus=bus, clock=clock)
        from scalpr.domain.order import ModifyOrderRequest
        mod = ModifyOrderRequest(quantity=20, price=Decimal("2600"))
        result = svc.modify("ord-1", mod)

        assert result is None
        modifies = bus.filter("exec.command.modify")
        assert len(modifies) == 1
        cmd = modifies[0].payload
        assert isinstance(cmd, ModifyOrder)
        assert cmd.order_id == "ord-1"
        assert cmd.updates["quantity"] == 20
        assert cmd.updates["price"] == Decimal("2600")
