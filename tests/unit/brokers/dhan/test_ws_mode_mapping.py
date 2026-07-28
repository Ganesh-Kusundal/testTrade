"""B-005/B-011: WebSocket mode mapping must be correct and resilient."""
import pytest


class TestGetSdkModeInt:
    """_get_sdk_mode_int() maps mode strings to dhanhq SDK integer constants."""

    def test_ltp_returns_ticker_constant(self):
        from scalpr.brokers.dhan.ws_client import _get_sdk_mode_int
        from dhanhq.marketfeed import Ticker
        assert _get_sdk_mode_int("ltp") == Ticker

    def test_quote_returns_quote_constant(self):
        from scalpr.brokers.dhan.ws_client import _get_sdk_mode_int
        from dhanhq.marketfeed import Quote
        assert _get_sdk_mode_int("quote") == Quote

    def test_depth_returns_quote_constant_not_depth(self):
        """B-011: depth must map to Quote (17), not Depth (19) — SDK doesn't distinguish."""
        from scalpr.brokers.dhan.ws_client import _get_sdk_mode_int
        from dhanhq.marketfeed import Quote
        assert _get_sdk_mode_int("depth") == Quote  # NOT Depth

    def test_full_returns_full_constant(self):
        from scalpr.brokers.dhan.ws_client import _get_sdk_mode_int
        from dhanhq.marketfeed import Full
        assert _get_sdk_mode_int("full") == Full

    def test_unknown_mode_defaults_to_quote(self):
        from scalpr.brokers.dhan.ws_client import _get_sdk_mode_int
        from dhanhq.marketfeed import Quote
        assert _get_sdk_mode_int("unknown") == Quote

    def test_mode_constants_are_correct_values(self):
        """Verify the actual wire values: Ticker=15, Quote=17, Depth=19, Full=21."""
        from dhanhq.marketfeed import Ticker, Quote, Full, Depth
        assert Ticker == 15
        assert Quote == 17
        assert Depth == 19
        assert Full == 21


class TestSdkMarketFeedClass:
    """_sdk_market_feed_class() lazy-imports the SDK feed class."""

    def test_returns_dhan_feed_or_market_feed(self):
        from scalpr.brokers.dhan.ws_client import _sdk_market_feed_class
        cls = _sdk_market_feed_class()
        # Must be a class (either DhanFeed or MarketFeed fallback)
        assert cls is not None
        assert isinstance(cls, type)
