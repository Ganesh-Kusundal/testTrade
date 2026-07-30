from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TypedDict

from scalpr.domain.instrument import InstrumentId
from scalpr.domain.tick import Tick
from scalpr.domain.values import ZERO


class Quote(TypedDict):
    symbol: str
    ltp: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    change: Decimal
    change_percent: Decimal
    oi: int


QuoteTick = Tick


def to_quote(data: dict, instrument_id: InstrumentId) -> Quote | QuoteTick:
    if "type" in data and data.get("security_id") is not None:
        return _ws_tick_from_data(data, instrument_id)
    return _rest_quote_from_data(data, instrument_id)


def _rest_quote_from_data(data: dict, instrument_id: InstrumentId) -> Quote:
    ohlc = data.get("ohlc", {})
    close = Decimal(str(ohlc.get("close", 0)))
    ltp = Decimal(str(data.get("last_price", 0)))
    net_change = Decimal(str(data.get("net_change", 0)))
    change_percent = (net_change / close * 100) if close else ZERO

    symbol = str(instrument_id).split(":")[0]

    return Quote(
        symbol=symbol,
        ltp=ltp,
        open=Decimal(str(ohlc.get("open", 0))),
        high=Decimal(str(ohlc.get("high", 0))),
        low=Decimal(str(ohlc.get("low", 0))),
        close=close,
        volume=int(data.get("volume", 0)),
        change=net_change,
        change_percent=change_percent,
        oi=int(data.get("oi", 0)),
    )


def _ws_tick_from_data(data: dict, instrument_id: InstrumentId) -> QuoteTick:
    symbol = str(instrument_id).split(":")[0]
    ltp = Decimal(str(data.get("LTP", "0")))

    depth = data.get("depth") or []
    if depth:
        bid = Decimal(str(depth[0].get("bid_price", "0")))
        ask = Decimal(str(depth[0].get("ask_price", "0")))
    else:
        bid = ask = ZERO

    raw_vol = data.get("volume", 0)
    cum_vol = int(raw_vol) if raw_vol is not None else 0

    return Tick(
        symbol=symbol,
        ltp=ltp,
        bid=bid,
        ask=ask,
        delta_volume=cum_vol,
        cumulative_volume=cum_vol,
        exchange_timestamp=datetime.now(timezone.utc),
    )
