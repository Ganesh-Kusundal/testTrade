from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from scalpr.adapters.dhan.client import DhanClient
from scalpr.domain.errors import InvalidOrder
from scalpr.domain.instrument import Exchange, ResolvedInstrument, Segment, SimpleInstrumentId
from scalpr.domain.order import OrderRequest, ProductType, Side
from scalpr.gateway.risk_service import RiskService


def make_resolved(
    symbol: str = "TCS",
    lot_size: int | None = 1,
    tick_size: Decimal | None = Decimal("0.05"),
    freeze_quantity: int | None = 100,
    segment: Segment = Segment.EQUITY,
) -> ResolvedInstrument:
    return ResolvedInstrument(
        instrument_id=SimpleInstrumentId(symbol=symbol, exchange=Exchange.NSE),
        security_id="112833",
        exchange=Exchange.NSE,
        segment=segment,
        trading_symbol=symbol,
        wire_segment="NSE_EQ",
        lot_size=lot_size,
        tick_size=tick_size,
        freeze_quantity=freeze_quantity,
        expiry=None,
        strike=None,
        option_type=None,
    )


class TestRiskServiceValidation:
    def test_valid_order_passes(self):
        client = MagicMock(spec=DhanClient)
        client.resolve_instrument.return_value = make_resolved(lot_size=1, tick_size=Decimal("0.05"))
        svc = RiskService(client)
        req = OrderRequest(
            instrument="TCS:NSE", side=Side.BUY, quantity=10,
            price=Decimal("2500.05"), product=ProductType.INTRADAY,
        )
        # Should not raise
        svc.validate(req)

    def test_rejects_non_positive_quantity(self):
        client = MagicMock(spec=DhanClient)
        svc = RiskService(client)
        req = OrderRequest(
            instrument="TCS:NSE", side=Side.BUY, quantity=0,
            price=Decimal("2500"),
        )
        with pytest.raises(InvalidOrder, match="quantity must be positive"):
            svc.validate(req)

    def test_rejects_non_lot_multiple(self):
        client = MagicMock(spec=DhanClient)
        svc = RiskService(client)
        client.resolve_instrument.return_value = make_resolved(lot_size=15)
        req = OrderRequest(
            instrument="NIFTY:NSE", side=Side.BUY, quantity=7,
            price=Decimal("24200"), product=ProductType.INTRADAY,
        )
        with pytest.raises(InvalidOrder, match="not a multiple of lot_size"):
            svc.validate(req)

    def test_rejects_exceeds_freeze_quantity(self):
        client = MagicMock(spec=DhanClient)
        svc = RiskService(client)
        client.resolve_instrument.return_value = make_resolved(freeze_quantity=100)
        req = OrderRequest(
            instrument="NIFTY:NSE", side=Side.BUY, quantity=200,
            price=Decimal("24200"), product=ProductType.INTRADAY,
        )
        with pytest.raises(InvalidOrder, match="exceeds freeze quantity"):
            svc.validate(req)

    def test_rejects_non_tick_aligned_price(self):
        client = MagicMock(spec=DhanClient)
        svc = RiskService(client)
        client.resolve_instrument.return_value = make_resolved(tick_size=Decimal("0.05"))
        req = OrderRequest(
            instrument="TCS:NSE", side=Side.BUY, quantity=10,
            price=Decimal("2500.03"),
        )
        with pytest.raises(InvalidOrder, match="not aligned to tick_size"):
            svc.validate(req)

    def test_market_order_skips_tick_check(self):
        client = MagicMock(spec=DhanClient)
        svc = RiskService(client)
        client.resolve_instrument.return_value = make_resolved(tick_size=Decimal("0.05"))
        from scalpr.domain.order import OrderType
        req = OrderRequest(
            instrument="TCS:NSE", side=Side.BUY, quantity=10,
            order_type=OrderType.MARKET, price=None,
        )
        # Should not raise
        svc.validate(req)
