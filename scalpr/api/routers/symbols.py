"""Symbol search — /symbols/search backed by the broker instruments CSV.

Loads the newest runtime-dev/instruments/instruments_*.csv once (lazy,
process-lifetime cache) and serves substring search over trading symbol
and name. No CSV → empty results with a logged warning, never mocks.
"""
from __future__ import annotations

import csv
import logging
import os
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from scalpr.api.models import SymbolInfo, SymbolSearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/symbols", tags=["symbols"])

_SEGMENT_MAP = {"E": "EQ", "D": "FO", "C": "CD", "M": "COM"}
_EXCHANGES = {"NSE", "BSE", "MCX"}

_cache_lock = threading.Lock()
_cache: list[SymbolInfo] | None = None


def _instruments_csv() -> Path | None:
    directory = Path(os.environ.get("SCALPR_INSTRUMENTS_DIR", "runtime-dev/instruments"))
    candidates = sorted(directory.glob("instruments_*.csv"))
    return candidates[-1] if candidates else None


def _load_symbols() -> list[SymbolInfo]:
    path = _instruments_csv()
    if path is None:
        logger.warning("symbols_csv_missing: no instruments CSV found")
        return []
    symbols: list[SymbolInfo] = []
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            exchange = row.get("SEM_EXM_EXCH_ID", "")
            segment = _SEGMENT_MAP.get(row.get("SEM_SEGMENT", ""))
            trading_symbol = row.get("SEM_TRADING_SYMBOL", "")
            if exchange not in _EXCHANGES or segment is None or not trading_symbol:
                continue
            try:
                lot_size = int(float(row.get("SEM_LOT_UNITS") or 1))
                tick_size = float(row.get("SEM_TICK_SIZE") or 0.05)
            except ValueError:
                continue
            symbols.append(SymbolInfo(
                symbol=trading_symbol,
                name=row.get("SM_SYMBOL_NAME") or trading_symbol,
                exchange=exchange,
                segment=segment,
                lotSize=lot_size,
                tickSize=tick_size,
            ))
    logger.info("symbols_loaded: %d from %s", len(symbols), path.name)
    return symbols


def _symbols() -> list[SymbolInfo]:
    global _cache
    with _cache_lock:
        if _cache is None:
            _cache = _load_symbols()
        return _cache


@router.get("/search", response_model=SymbolSearchResponse)  # type: ignore[untyped-decorator]
async def search_symbols(q: str = "", limit: int = Query(default=25, ge=1, le=200)) -> Any:
    needle = q.strip().upper()
    universe = _symbols()
    if not needle:
        return SymbolSearchResponse(results=universe[:limit])
    results = [
        s for s in universe
        if needle in s.symbol.upper() or needle in s.name.upper()
    ]
    return SymbolSearchResponse(results=results[:limit])
