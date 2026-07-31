"""S-1: Dhan SDK compatibility contract.

Pins the exact dhanhq surface scalpr consumes. If a dhanhq upgrade renames,
moves, or re-values any of these symbols, this test goes red at CI time —
instead of `ws_client` raising ImportError/AttributeError in live trading.

Every assertion here corresponds to a real call site in
scalpr/adapters/dhan/_ws.py.

The installed dhanhq 2.2.x exposes:
- ``MarketFeed`` class (top-level; legacy ``DhanFeed`` subpackage removed)
- Class attributes: ``MarketFeed.Ticker=15``, ``MarketFeed.Quote=17``, ``MarketFeed.Full=21``
- ``MarketFeed.__init__`` accepts ``dhan_context``, ``instruments``, ``version``
- ``FullDepth`` class (top-level; legacy ``dhanhq.fulldepth`` subpackage removed)
- ``DhanContext`` class (top-level)
"""
import inspect


def _feed_cls():
    """Return the SDK feed class (MarketFeed only — v2.2+ required)."""
    from dhanhq import MarketFeed
    return MarketFeed


def _full_depth_cls():
    """Return the SDK FullDepth class (top-level — v2.2+ required)."""
    from dhanhq import FullDepth
    return FullDepth


def _dhan_context_cls():
    """Return the SDK DhanContext class (top-level — v2.2+ required)."""
    from dhanhq import DhanContext
    return DhanContext


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
    """Feed class exposes exchange segment constants matching our wire map."""
    cls = _feed_cls()
    assert cls.NSE == 1
    assert cls.NSE_FNO == 2
    assert cls.MCX == 5


def test_constructor_accepts_instruments_and_version():
    """Feed class must accept ``instruments`` and ``version`` at construction time."""
    cls = _feed_cls()
    params = inspect.signature(cls.__init__).parameters
    assert "instruments" in params, (
        f"{cls.__name__}.__init__ lost 'instruments' kwarg"
    )
    assert "version" in params, (
        f"{cls.__name__}.__init__ lost 'version' kwarg"
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


def test_full_depth_importable_top_level():
    """FullDepth must be importable from top-level dhanhq (not subpackage)."""
    cls = _full_depth_cls()
    assert isinstance(cls, type)
    assert hasattr(cls, "get_exchange_segment")


def test_dhan_context_importable_top_level():
    """DhanContext must be importable from top-level dhanhq (no shim)."""
    cls = _dhan_context_cls()
    assert isinstance(cls, type)
    params = inspect.signature(cls.__init__).parameters
    assert "client_id" in params
    assert "access_token" in params


def test_segment_to_numeric_matches_market_feed_constants():
    """Resolver SEGMENT_TO_NUMERIC must match dhanhq MarketFeed exchange ints."""
    from scalpr.adapters.dhan._resolver import SEGMENT_TO_NUMERIC

    cls = _feed_cls()
    assert SEGMENT_TO_NUMERIC["NSE_EQ"] == cls.NSE
    assert SEGMENT_TO_NUMERIC["NSE_FNO"] == cls.NSE_FNO
    assert SEGMENT_TO_NUMERIC["MCX_COMM"] == cls.MCX
    assert SEGMENT_TO_NUMERIC["BSE_EQ"] == cls.BSE
    assert SEGMENT_TO_NUMERIC["IDX_I"] == cls.IDX
