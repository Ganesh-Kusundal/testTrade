"""C3 fail-closed router contract: broker outage must surface as 5xx, never as fabricated data."""
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _app(gateway):
    from scalpr.api.routers import market_data, orders, portfolio
    from scalpr.api.routers.health import router as health_router

    app = FastAPI()
    app.include_router(market_data.router)
    app.include_router(orders.router)
    app.include_router(portfolio.router)
    app.include_router(health_router)
    app.state.gateway = gateway
    app.state.feed = None
    app.state.broker_error = None if gateway else "no credentials"
    return app


@pytest.fixture
def connected_gateway():
    gw = MagicMock()
    gw.is_connected.return_value = True
    return gw


class TestGatewayUnavailable503:
    @pytest.mark.parametrize("path", [
        "/portfolio/positions", "/portfolio/margins", "/orders/", "/market/ltp/RELIANCE",
    ])
    def test_none_gateway_returns_503(self, path):
        client = TestClient(_app(gateway=None))
        assert client.get(path).status_code == 503

    def test_disconnected_gateway_returns_503(self):
        gw = MagicMock()
        gw.is_connected.return_value = False
        client = TestClient(_app(gateway=gw))
        assert client.get("/portfolio/positions").status_code == 503


class TestAdapterFailure502:
    def test_positions_adapter_raise_returns_502(self, connected_gateway):
        connected_gateway.get_positions.side_effect = Exception("API down")
        client = TestClient(_app(connected_gateway))
        assert client.get("/portfolio/positions").status_code == 502

    def test_margins_adapter_raise_returns_502(self, connected_gateway):
        connected_gateway.get_margins.side_effect = Exception("API down")
        client = TestClient(_app(connected_gateway))
        assert client.get("/portfolio/margins").status_code == 502

    def test_ltp_adapter_raise_returns_502(self, connected_gateway):
        connected_gateway.get_ltp.side_effect = Exception("API down")
        client = TestClient(_app(connected_gateway))
        assert client.get("/market/ltp/RELIANCE").status_code == 502


class TestFillsNotImplemented:
    def test_fills_returns_501(self, connected_gateway):
        client = TestClient(_app(connected_gateway))
        assert client.get("/orders/fills").status_code == 501


class TestHealthTruthful:
    def test_health_without_gateway(self):
        client = TestClient(_app(gateway=None))
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"gateway": False, "feed": False, "broker_error": "no credentials"}

    def test_health_with_connected_gateway(self, connected_gateway):
        client = TestClient(_app(connected_gateway))
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"gateway": True, "feed": False, "broker_error": None}


class TestProbes:
    """k8s-style probes matching the TestSprite cloud contract:
    live is always 200 {status: ok, check: live}; ready is 200 when the
    gateway is connected, 503 with the same JSON shape when it is not.
    """

    def test_live_always_200(self):
        client = TestClient(_app(gateway=None))
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "check": "live"}

    def test_ready_200_when_gateway_connected(self, connected_gateway):
        client = TestClient(_app(connected_gateway))
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "check": "ready"}

    def test_ready_503_when_gateway_down_body_keeps_shape(self):
        client = TestClient(_app(gateway=None))
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        body = resp.json()
        assert body["check"] == "ready"
        assert body["status"] == "unavailable"

