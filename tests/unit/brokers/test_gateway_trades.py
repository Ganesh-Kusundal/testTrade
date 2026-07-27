"""C5 regression: Trade.exchange must come from the fill's exchange, never str(side).

# captured live 2025 wire shape: tradebook entries carry exchangeSegment
# (e.g. "NSE_EQ") which the dhan adapter maps to an exchange string.
"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import create_autospec

from scalpr.brokers.broker_port import IBrokerGateway
from scalpr.brokers.dhan.gateway import DhanGateway
from scalpr.brokers.gateway import Gateway
from scalpr.domain.fill import Fill
from scalpr.domain.order import OrderSide


def _gateway_with_port(port: IBrokerGateway) -> Gateway:
    g = object.__new__(Gateway)
    g._broker_name = "dhan"
    g._gateway = port
    g._ws_manager = None
    g._stream_callbacks = []
    return g


def test_trades_exchange_comes_from_fill_not_side() -> None:
    fill = Fill(
        fill_id="T1",
        order_id="O1",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        price=Decimal("2500"),
        timestamp=datetime(2025, 1, 15, tzinfo=timezone.utc),
        exchange="NSE",
    )
    port = create_autospec(IBrokerGateway, instance=True)
    port.get_tradebook.return_value = [fill]

    trades = _gateway_with_port(port).trades()

    assert trades[0].exchange == "NSE"


def test_trades_exchange_empty_when_unknown() -> None:
    fill = Fill(
        fill_id="T2",
        order_id="O2",
        symbol="TCS",
        side=OrderSide.SELL,
        quantity=5,
        price=Decimal("4000"),
    )
    port = create_autospec(IBrokerGateway, instance=True)
    port.get_tradebook.return_value = [fill]

    trades = _gateway_with_port(port).trades()

    assert trades[0].exchange == ""  # honest unknown, never fabricated


def test_map_raw_trade_populates_exchange_from_segment() -> None:
    raw = {
        "trade_id": "T3",
        "order_id": "O3",
        "symbol": "RELIANCE",
        "side": "BUY",
        "quantity": 10,
        "price": Decimal("2500"),
        "trade_date": "2025-01-15T10:30:00",
        "exchange_segment": "NSE_EQ",
    }
    fill = DhanGateway._map_raw_trade_to_fill(raw)
    assert fill.exchange == "NSE"


def test_map_raw_trade_missing_segment_yields_empty_exchange() -> None:
    raw = {
        "trade_id": "T4",
        "order_id": "O4",
        "symbol": "TCS",
        "side": "SELL",
        "quantity": 5,
        "price": Decimal("4000"),
    }
    fill = DhanGateway._map_raw_trade_to_fill(raw)
    assert fill.exchange == ""
