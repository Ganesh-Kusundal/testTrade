"""S-1: Dhan SDK compatibility contract.

Pins the exact dhanhq surface scalpr consumes. If a dhanhq upgrade renames,
moves, or re-values any of these symbols, this test goes red at CI time —
instead of `ws_client` raising ImportError/AttributeError in live trading
(which is exactly what happened when dhanhq 2.2.0 moved Ticker/Quote/Full
from module level onto the MarketFeed class).

Every assertion here corresponds to a real call site in
scalpr/brokers/dhan/ws_client.py.
"""
import inspect


def test_marketfeed_class_importable():
    from dhanhq.marketfeed import MarketFeed

    assert isinstance(MarketFeed, type)


def test_mode_constants_exist_with_v2_wire_values():
    """ws_client._sdk_mode_constants reads Ticker/Quote/Full off the class."""
    from dhanhq.marketfeed import MarketFeed

    assert MarketFeed.Ticker == 15
    assert MarketFeed.Quote == 17
    assert MarketFeed.Full == 21


def test_exchange_segment_constants_exist():
    """Numeric segment codes used when building subscription tuples."""
    from dhanhq.marketfeed import MarketFeed

    for name in ("IDX", "NSE", "NSE_FNO", "BSE", "MCX", "BSE_FNO"):
        assert hasattr(MarketFeed, name), f"MarketFeed.{name} missing"


def test_constructor_accepts_ws_client_kwargs():
    """ws_client.connect() instantiates MarketFeed with these kwargs."""
    from dhanhq.marketfeed import MarketFeed

    params = inspect.signature(MarketFeed.__init__).parameters
    for kwarg in (
        "dhan_context",
        "instruments",
        "on_connect",
        "on_message",
        "on_close",
        "on_error",
    ):
        assert kwarg in params, f"MarketFeed.__init__ lost kwarg {kwarg!r}"


def test_runtime_methods_exist():
    """Methods ws_client calls on the live feed object."""
    from dhanhq.marketfeed import MarketFeed

    for method in (
        "run",
        "close_connection",
        "subscribe_symbols",
        "unsubscribe_symbols",
    ):
        assert callable(getattr(MarketFeed, method, None)), (
            f"MarketFeed.{method} missing or not callable"
        )
