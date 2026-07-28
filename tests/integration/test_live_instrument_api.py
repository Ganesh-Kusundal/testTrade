"""Live integration tests for Gateway.instrument() against the real Dhan API.

S-5: previously these "tests" returned True/False (pytest treats a returning
test as passing regardless), so failures were invisible. Now they assert.

Gated: skipped unless DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN are set.
Read-only — no orders are placed.

Run: pytest tests/integration/test_live_instrument_api.py -m live_readonly
"""
import os
import time
from decimal import Decimal

import pandas as pd
import pytest
from dotenv import load_dotenv

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
def gateway():
    from scalpr.brokers import Gateway

    return Gateway()


@pytest.fixture(autouse=True)
def _pace_dhan_rate_limit():
    """Respect Dhan's 1 req/sec market-feed rate limit between tests."""
    yield
    time.sleep(1.1)


def test_instrument_resolution(gateway):
    tcs = gateway.instrument("TCS:NSE")
    assert tcs.symbol == "TCS"
    assert tcs.exchange == "NSE"
    assert tcs.resolved.security_id is not None
    assert tcs.resolved.wire_segment is not None
    assert tcs.resolved.lot_size >= 1


def test_ltp(gateway):
    ltp = gateway.instrument("TCS:NSE").ltp()
    assert isinstance(ltp, Decimal)
    assert ltp > 0


def test_quote(gateway):
    quote = gateway.instrument("TCS:NSE").quote()
    assert isinstance(quote, dict)
    assert "ltp" in quote
    assert Decimal(str(quote["ltp"])) > 0


def test_historical(gateway):
    df = gateway.instrument("TCS:NSE").historical(interval="1D")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    for col in ("open", "high", "low", "close", "volume"):
        assert col in df.columns, f"column {col!r} missing"


@pytest.mark.parametrize("symbol", ["TCS:NSE", "RELIANCE:NSE", "INFY:NSE"])
def test_multiple_instruments(gateway, symbol):
    handle = gateway.instrument(symbol)
    ltp = handle.ltp()
    assert isinstance(ltp, Decimal)
    assert ltp > 0
    time.sleep(1.1)  # pace within the parametrized batch too


def test_index_instrument(gateway):
    nifty = gateway.instrument("NIFTY:NSE")
    assert nifty.resolved.security_id is not None
    ltp = nifty.ltp()
    assert isinstance(ltp, Decimal)
    assert ltp > 0
