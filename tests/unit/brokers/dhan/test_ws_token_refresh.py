"""S-2 (B-014): WS stack must pick up refreshed tokens on (re)connect.

Dhan access tokens expire (DH-906). The HTTP clients already accept a
token_refresh_fn; before this fix the WS client/manager never did, so a
reconnect after token expiry re-sent the stale token forever.
"""
from unittest.mock import MagicMock

from scalpr.brokers.dhan.ws_client import DhanWebSocketClient, _DhanContextShim
from scalpr.brokers.dhan.ws_manager import DhanWebSocketManager


class TestClientTokenRefresh:
    def test_maybe_refresh_updates_token(self):
        client = DhanWebSocketClient(
            access_token="stale",
            client_id="c1",
            token_refresh_fn=lambda: "fresh",
        )
        client._maybe_refresh_token()
        assert client._token == "fresh"

    def test_maybe_refresh_updates_live_context_shim(self):
        client = DhanWebSocketClient(
            access_token="stale",
            client_id="c1",
            token_refresh_fn=lambda: "fresh",
        )
        client._context = _DhanContextShim("c1", "stale")
        client._maybe_refresh_token()
        assert client._context.get_access_token() == "fresh"

    def test_no_refresh_fn_keeps_token(self):
        client = DhanWebSocketClient(access_token="stale", client_id="c1")
        client._maybe_refresh_token()
        assert client._token == "stale"

    def test_refresh_failure_keeps_current_token(self):
        def boom() -> str:
            raise RuntimeError("auth service down")

        client = DhanWebSocketClient(
            access_token="stale", client_id="c1", token_refresh_fn=boom
        )
        client._maybe_refresh_token()
        assert client._token == "stale"

    def test_refresh_returning_empty_keeps_current_token(self):
        client = DhanWebSocketClient(
            access_token="stale", client_id="c1", token_refresh_fn=lambda: ""
        )
        client._maybe_refresh_token()
        assert client._token == "stale"

    async def test_connect_refreshes_before_creating_feed(self, monkeypatch):
        """connect() must consume the fresh token when building the SDK feed."""
        seen: dict = {}

        class FakeFeed:
            def __init__(self, dhan_context=None, instruments=None, **kwargs):
                seen["token"] = dhan_context.get_access_token()

            def run(self):
                pass

            def close_connection(self):
                pass

        monkeypatch.setattr(
            "scalpr.brokers.dhan.ws_client._sdk_market_feed_class",
            lambda: FakeFeed,
        )
        client = DhanWebSocketClient(
            access_token="stale", client_id="c1", token_refresh_fn=lambda: "fresh"
        )
        # Short-circuit the connection wait: mark connected as soon as
        # the background thread would start.
        monkeypatch.setattr(
            DhanWebSocketClient,
            "_run_sdk",
            lambda self: setattr(self, "_connected", True),
        )
        assert await client.connect() is True
        assert seen["token"] == "fresh"
        await client.disconnect()


class TestManagerTokenRefresh:
    def test_manager_passes_refresh_fn_to_client(self):
        fn = MagicMock(return_value="fresh")
        mgr = DhanWebSocketManager(
            access_token="stale", client_id="c1", token_refresh_fn=fn
        )
        mgr._ensure_components()
        assert mgr._ws_client._token_refresh_fn is fn
