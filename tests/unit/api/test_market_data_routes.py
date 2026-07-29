"""B-002: Market data routes must forward exchange query param to gateway."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _app(gateway):
    from scalpr.api.routers import market_data
    from scalpr.api.routers.health import router as health_router

    app = FastAPI()
    app.include_router(market_data.router)
    app.include_router(health_router)
    app.state.gateway = gateway
    app.state.feed = None
    app.state.broker_error = None
    return app


@pytest.fixture
def connected_gateway():
    gw = MagicMock()
    gw.is_connected.return_value = True
    return gw


class TestExchangeQueryParam:
    """B-002: exchange query param must be forwarded to gateway, not hardcoded NSE."""

    def test_ltp_default_exchange_is_nse(self, connected_gateway):
        connected_gateway.get_ltp.return_value = Decimal("2500.00")
        client = TestClient(_app(connected_gateway))
        resp = client.get("/market/ltp/TCS")
        assert resp.status_code == 200
        body = resp.json()
        assert body["exchange"] == "NSE"
        connected_gateway.get_ltp.assert_called_once_with("TCS", "NSE")

    def test_ltp_forwards_mcx_exchange(self, connected_gateway):
        connected_gateway.get_ltp.return_value = Decimal("5500.00")
        client = TestClient(_app(connected_gateway))
        resp = client.get("/market/ltp/CRUDEOIL?exchange=MCX")
        assert resp.status_code == 200
        body = resp.json()
        assert body["exchange"] == "MCX"
        connected_gateway.get_ltp.assert_called_once_with("CRUDEOIL", "MCX")

    def test_ltp_forwards_nse_fno_exchange(self, connected_gateway):
        connected_gateway.get_ltp.return_value = Decimal("24200.00")
        client = TestClient(_app(connected_gateway))
        resp = client.get("/market/ltp/NIFTY?exchange=NSE")
        assert resp.status_code == 200
        body = resp.json()
        assert body["exchange"] == "NSE"
        connected_gateway.get_ltp.assert_called_once_with("NIFTY", "NSE")

    def test_ltp_forwards_index_exchange(self, connected_gateway):
        connected_gateway.get_ltp.return_value = Decimal("24500.00")
        client = TestClient(_app(connected_gateway))
        resp = client.get("/market/ltp/NIFTY?exchange=INDEX")
        assert resp.status_code == 200
        body = resp.json()
        assert body["exchange"] == "INDEX"
        connected_gateway.get_ltp.assert_called_once_with("NIFTY", "INDEX")

    def test_candles_forwards_exchange(self, connected_gateway):
        connected_gateway.connection.historical.get_ohlcv_latest.return_value = []
        client = TestClient(_app(connected_gateway))
        resp = client.get("/market/candles/TCS?exchange=MCX&timeframe=15m&count=50")
        assert resp.status_code == 200
        connected_gateway.connection.historical.get_ohlcv_latest.assert_called_once_with(
            "TCS", "MCX", "15m", 50
        )

    def test_candles_default_exchange_is_nse(self, connected_gateway):
        connected_gateway.connection.historical.get_ohlcv_latest.return_value = []
        client = TestClient(_app(connected_gateway))
        resp = client.get("/market/candles/TCS")
        assert resp.status_code == 200
        connected_gateway.connection.historical.get_ohlcv_latest.assert_called_once_with(
            "TCS", "NSE", "5m", 100
        )
