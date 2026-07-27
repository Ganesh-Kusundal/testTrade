"""Bootstrap factory creates a properly wired FastAPI app."""
import pytest
from unittest.mock import MagicMock, create_autospec, patch

from scalpr.brokers.broker_port import IBrokerGateway


def _get_all_route_paths(app):
    """Extract all route paths from a FastAPI app, including included routers."""
    paths = []
    for r in app.routes:
        if hasattr(r, "path"):
            paths.append(r.path)
        # FastAPI stores included routers as _IncludedRouter with original_router
        if hasattr(r, "original_router") and hasattr(r.original_router, "routes"):
            for sub_r in r.original_router.routes:
                if hasattr(sub_r, "path"):
                    paths.append(sub_r.path)
    return paths


def test_create_app_should_return_fastapi_app():
    """create_app() must return a FastAPI instance with all routers."""
    with patch("scalpr.api.bootstrap._load_dotenv"), \
         patch("scalpr.api.bootstrap._create_gateway") as mock_gw:
        mock_gw.return_value = (MagicMock(), None)

        from scalpr.api.bootstrap import create_app
        app = create_app()

        assert app is not None
        route_paths = _get_all_route_paths(app)
        assert any("/market" in p for p in route_paths), f"No /market route in {route_paths}"
        assert any("/orders" in p for p in route_paths), f"No /orders route in {route_paths}"
        assert any("/portfolio" in p for p in route_paths), f"No /portfolio route in {route_paths}"


def test_create_app_should_not_have_side_effects_on_import():
    """Importing bootstrap must not create network connections."""
    import importlib
    import scalpr.api.bootstrap as mod
    importlib.reload(mod)
    assert hasattr(mod, "create_app")


class TestWire:
    """C1: wire() must produce a connected object graph, no guessed kwargs."""

    def test_wire_builds_connected_graph(self, tmp_path):
        from scalpr.api.bootstrap import wire

        gw = create_autospec(IBrokerGateway, instance=True)
        ctx = wire(gw, ["RELIANCE", "TCS"], db_path=str(tmp_path / "oms.db"))

        # Router wired to the port and to persistence
        assert ctx.order_router.gateway is gw
        assert ctx.order_router.order_manager is not None
        assert ctx.order_router.risk_gate is not None
        assert ctx.order_router.circuit_breaker is not None

        # One strategy per watchlist symbol, all sharing the router
        assert len(ctx.executor.strategies) == 2
        symbols = {s.symbol for s in ctx.executor.strategies}
        assert symbols == {"RELIANCE", "TCS"}
        assert all(s.order_router is ctx.order_router for s in ctx.executor.strategies)


class TestLifespanGating:
    """Trading wiring only under explicit env flag — plain boots unchanged."""

    def test_trading_unset_constructs_nothing(self, monkeypatch):
        monkeypatch.delenv("SCALPR_TRADING_ENABLED", raising=False)
        with patch("scalpr.api.bootstrap._load_dotenv"), \
             patch("scalpr.api.bootstrap._create_gateway") as mock_gw:
            mock_gw.return_value = (None, "no creds")

            from fastapi.testclient import TestClient
            from scalpr.api.bootstrap import create_app

            app = create_app()
            with TestClient(app):
                assert app.state.feed is None
                assert getattr(app.state, "executor", None) is None
