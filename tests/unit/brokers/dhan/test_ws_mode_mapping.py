"""B-005/B-011/S-1: WebSocket mode mapping must be correct and resilient.

Constants are asserted against the *installed* SDK surface (MarketFeed class
attributes in dhanhq 2.2.x), not a copy of them — so an SDK upgrade that
moves or changes the constants turns these tests red instead of breaking live.
"""

from scalpr.brokers.dhan.ws_client import (
    _get_sdk_mode_int,
    _sdk_market_feed_class,
    _sdk_mode_constants,
)


class TestGetSdkModeInt:
    """_get_sdk_mode_int() maps mode strings to dhanhq SDK integer constants."""

    def test_ltp_returns_ticker_constant(self):
        ticker, _, _ = _sdk_mode_constants()
        assert _get_sdk_mode_int("ltp") == ticker

    def test_quote_returns_quote_constant(self):
        _, quote, _ = _sdk_mode_constants()
        assert _get_sdk_mode_int("quote") == quote

    def test_depth_returns_quote_constant_not_depth(self):
        """B-011: depth must map to Quote, not Depth — SDK doesn't distinguish."""
        _, quote, _ = _sdk_mode_constants()
        assert _get_sdk_mode_int("depth") == quote

    def test_full_returns_full_constant(self):
        _, _, full = _sdk_mode_constants()
        assert _get_sdk_mode_int("full") == full

    def test_unknown_mode_defaults_to_quote(self):
        _, quote, _ = _sdk_mode_constants()
        assert _get_sdk_mode_int("unknown") == quote

    def test_mode_constants_are_correct_wire_values(self):
        """Dhan v2 wire values: Ticker=15, Quote=17, Full=21."""
        assert _sdk_mode_constants() == (15, 17, 21)

    def test_mode_constants_sourced_from_installed_sdk(self):
        """Constants must agree with the installed SDK module-level values."""
        from dhanhq.marketfeed import Full, Quote, Ticker
        assert _sdk_mode_constants() == (Ticker, Quote, Full)


class TestSdkMarketFeedClass:
    """_sdk_market_feed_class() lazy-imports the SDK feed class."""

    def test_returns_market_feed_class(self):
        cls = _sdk_market_feed_class()
        assert cls is not None
        assert isinstance(cls, type)
