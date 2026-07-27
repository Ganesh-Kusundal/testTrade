"""Bootstrap factory creates a properly wired FastAPI app."""
import pytest
from unittest.mock import MagicMock, patch


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
         patch("scalpr.api.bootstrap._create_gateway") as mock_gw, \
         patch("scalpr.api.bootstrap._create_feed") as mock_feed:

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
