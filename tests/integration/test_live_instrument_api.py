"""Live integration tests for DhanClient instrument resolution and market data.

Gated: skipped unless DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN are set.
Read-only — no orders are placed.

Run: pytest tests/integration/test_live_instrument_api.py -m live_readonly
"""
import os
import time
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import pytest
from dotenv import load_dotenv

from scalpr.domain.instrument import Exchange, SimpleInstrumentId

load_dotenv()

_HAS_CREDS = bool(os.getenv("DHAN_CLIENT_ID")) and bool(os.getenv("DHAN_ACCESS_TOKEN"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.live_readonly,
    pytest.mark.dhan,
    pytest.mark.skipif(
        not _HAS_CREDS,
        reason="requires DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in environment",
    ),
]


@pytest.fixture(scope="module")
def client():
    from scalpr.adapters.dhan.client import DhanClient
    from scalpr.engine.clock import LiveClock
    from scalpr.engine.message_bus import MessageBus

    bus = MessageBus()
    clock = LiveClock()
    config = {
        "client_id": os.environ["DHAN_CLIENT_ID"],
        "access_token": os.environ["DHAN_ACCESS_TOKEN"],
        "totp_secret": os.environ.get("DHAN_TOTP_SECRET", ""),
        "pin": os.environ.get("DHAN_PIN", "1111"),
        "csv_path": os.environ.get("DHAN_INSTRUMENT_CSV", "instrument.csv"),
    }
    c = DhanClient(bus, clock, config)
    c.start()
    yield c
    c.stop()


@pytest.fixture(autouse=True)
def _pace_dhan_rate_limit():
    yield
    time.sleep(1.1)


def test_instrument_resolution(client):
    resolved = client._resolver.resolve_full("TCS", "NSE")
    assert resolved.trading_symbol == "TCS"
    assert resolved.exchange == Exchange.NSE
    assert resolved.security_id is not None
    assert resolved.wire_segment is not None
    assert resolved.lot_size is not None and resolved.lot_size >= 1


def test_ltp(client):
    ltp = client._historical.get_ltp("TCS", "NSE")
    assert isinstance(ltp, (int, float))
    assert ltp > 0


def test_quote(client):
    quote = client.get_quote(SimpleInstrumentId("TCS", Exchange.NSE))
    assert isinstance(quote, dict)
    assert quote.get("ltp") is not None
    assert Decimal(str(quote["ltp"])) > 0


def test_historical(client):
    from_date = date.today() - timedelta(days=30)
    to_date = date.today()
    candles = client.get_daily("TCS", "NSE", from_date=from_date.isoformat(), to_date=to_date.isoformat())
    df = pd.DataFrame(candles)
    assert not df.empty
    for col in ("open", "high", "low", "close", "volume"):
        assert col in df.columns, f"column {col!r} missing"


@pytest.mark.parametrize("symbol,exchange", [
    ("TCS", "NSE"),
    ("RELIANCE", "NSE"),
    ("INFY", "NSE"),
])
def test_multiple_instruments(client, symbol, exchange):
    ltp = client._historical.get_ltp(symbol, exchange)
    assert isinstance(ltp, (int, float))
    assert ltp > 0
    time.sleep(1.1)


def test_index_instrument(client):
    resolved = client._resolver.resolve_full("NIFTY 50", "NSE")
    assert resolved.security_id is not None
    ltp = client._historical.get_ltp("NIFTY 50", "NSE")
    assert isinstance(ltp, (int, float))
    assert ltp > 0
