"""S-1: Dhan SDK compatibility contract.

Pins the exact dhanhq surface scalpr consumes. If a dhanhq upgrade renames,
moves, or re-values any of these symbols, this test goes red at CI time —
instead of `ws_client` raising ImportError/AttributeError in live trading.

Every assertion here corresponds to a real call site in
scalpr/brokers/dhan/ws_client.py.

The installed dhanhq 2.2.x exposes:
- ``MarketFeed`` class (also aliased as ``DhanFeed`` in some versions)
- Class attributes: ``MarketFeed.Ticker=15``, ``MarketFeed.Quote=17``, ``MarketFeed.Full=21``
- ``MarketFeed.__init__`` accepts ``client_id``, ``access_token``, ``instruments``
"""
import inspect


def _feed_cls():
    """Return the SDK feed class (DhanFeed or MarketFeed)."""
    try:
        from dhanhq.marketfeed import MarketFeed
        return MarketFeed
    except ImportError:
        from dhanhq.marketfeed import DhanFeed
        return DhanFeed


def test_feed_class_importable():
    cls = _feed_cls()
    assert isinstance(cls, type)


def test_mode_constants_exist_with_v2_wire_values():
    """Feed class Ticker/Quote/Full attributes must have the v2 wire values."""
    cls = _feed_cls()

    assert cls.Ticker == 15
    assert cls.Quote == 17
    assert cls.Full == 21


def test_exchange_segment_constants_exist():
    """Feed class exposes get_exchange_segment for subscription tuples."""
    cls = _feed_cls()
    assert hasattr(cls, "get_exchange_segment") or hasattr(cls, "get_data")


def test_constructor_accepts_instruments():
    """Feed class must accept ``instruments`` at construction time."""
    cls = _feed_cls()
    params = inspect.signature(cls.__init__).parameters
    assert "instruments" in params, (
        f"{cls.__name__}.__init__ lost 'instruments' kwarg"
    )


def test_runtime_methods_exist():
    """Methods ws_client calls on the live feed object."""
    cls = _feed_cls()
    for method in (
        "connect",
        "close_connection",
        "subscribe_symbols",
        "unsubscribe_symbols",
    ):
        assert callable(getattr(cls, method, None)), (
            f"{cls.__name__}.{method} missing or not callable"
        )
