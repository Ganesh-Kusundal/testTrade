"""Instrument master CSV loader with daily caching.

Downloads Dhan instrument master CSV and caches it locally for fast startup.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from config.endpoints import Dhan
from scalpr.brokers.dhan.segments import _COMPACT_SEGMENT_MAP

logger = logging.getLogger(__name__)

_COMPACT_CSV_URL = Dhan.INSTRUMENT_CSV


class InstrumentLoader:
    """Downloads and parses Dhan instrument master with daily caching.

    Features:
    - Daily cache with 6-hour TTL
    - Automatic cleanup of old cache files
    - Fallback to stale cache on download failure
    """

    @staticmethod
    def _cleanup_old_cache(cache_dir: Path, days: int = 7) -> None:
        """Purge cached files older than N days."""
        now = time.time()
        cutoff = now - (days * 24 * 3600)
        try:
            for path in cache_dir.glob("instruments_*.csv"):
                if path.is_file():
                    mtime = path.stat().st_mtime
                    if mtime < cutoff:
                        logger.info(f"Cleaning up old instrument cache file: {path}")
                        path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning(f"Failed to clean up old cache files: {exc}")

    @staticmethod
    def load_cached(force_refresh: bool = False) -> list[dict]:
        """Load instrument master rows with daily caching.

        Args:
            force_refresh: If True, ignore cache and re-download

        Returns:
            List of instrument row dicts
        """
        # Determine cache directory
        env_cache = os.environ.get("DHAN_CACHE_DIR")
        if env_cache:
            cache_dir = Path(env_cache)
        else:
            # Default to project root / runtime-dev / instruments
            cache_dir = Path(__file__).resolve().parents[3] / "runtime-dev" / "instruments"

        cache_dir.mkdir(parents=True, exist_ok=True)

        # Clean up old caches
        InstrumentLoader._cleanup_old_cache(cache_dir, days=7)

        today = date.today().isoformat()
        cache_path = cache_dir / f"instruments_{today}.csv"

        # Check cache TTL (6 hours)
        if not force_refresh and cache_path.exists() and cache_path.stat().st_size > 0:
            try:
                mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
                cache_age_hours = (datetime.now() - mtime).total_seconds() / 3600.0
                if cache_age_hours > 6.0:
                    logger.info(f"Cache is older than 6 hours (age: {cache_age_hours:.1f} hours). Refreshing...")
                    force_refresh = True
            except Exception as exc:
                logger.warning(f"Error checking cache file modification time: {exc}")

        df = None
        if not force_refresh and cache_path.exists() and cache_path.stat().st_size > 0:
            logger.info(f"Loading instruments from cache: {cache_path}")
            try:
                df = pd.read_csv(cache_path, low_memory=False)
            except Exception as exc:
                logger.warning(f"Failed to read cached file: {exc}. Will re-download.")

        if df is None:
            logger.info("Downloading instruments from Dhan...")
            try:
                df = pd.read_csv(_COMPACT_CSV_URL, low_memory=False)
                tmp_path = cache_path.with_suffix(".csv.tmp")
                df.to_csv(tmp_path, index=False)
                os.replace(tmp_path, cache_path)
            except Exception as exc:
                if cache_path.exists() and cache_path.stat().st_size > 0:
                    logger.error(f"Failed to download instruments ({exc}). Using stale cache.")
                    try:
                        df = pd.read_csv(cache_path, low_memory=False)
                    except Exception as read_exc:
                        raise exc from read_exc
                else:
                    raise exc

        rows = InstrumentLoader._compact_to_rows(df)
        logger.info(f"Loaded {len(rows)} instruments")
        return rows

    @staticmethod
    def load_from_file(path: str | Path) -> list[dict]:
        """Load instruments from a local CSV file."""
        df = pd.read_csv(path, low_memory=False)
        return InstrumentLoader._compact_to_rows(df)

    @staticmethod
    def load_from_url(url: str) -> list[dict]:
        """Load instruments from a URL."""
        df = pd.read_csv(url, low_memory=False)
        return InstrumentLoader._compact_to_rows(df)

    @staticmethod
    def _compact_to_rows(df) -> list[dict]:
        """Convert DataFrame to list of row dicts with standardized fields."""
        out: list[dict] = []
        for r in df.itertuples(index=False):
            exch_id = str(getattr(r, "SEM_EXM_EXCH_ID", ""))
            segment = str(getattr(r, "SEM_SEGMENT", ""))
            seg = _COMPACT_SEGMENT_MAP.get((exch_id, segment))
            if seg is None:
                continue

            out.append({
                "SEM_TRADING_SYMBOL": str(getattr(r, "SEM_TRADING_SYMBOL", "")),
                "SEM_SMST_SECURITY_ID": str(int(getattr(r, "SEM_SMST_SECURITY_ID", 0))),
                "SEM_EXM_EXCH_ID": exch_id,  # raw exchange id (NSE/BSE/MCX), as the name promises
                "SEM_SEGMENT": segment,  # raw segment code (E/D/I/M/C)
                "WIRE_SEGMENT": seg,  # explicit Dhan wire segment (NSE_EQ/BSE_EQ/IDX_I/...)
                "SEM_INSTRUMENT_NAME": str(getattr(r, "SEM_INSTRUMENT_NAME", "")),
                "SEM_LOT_UNITS": _safe_float(r, "SEM_LOT_UNITS", 1),
                "SEM_TICK_SIZE": _safe_float(r, "SEM_TICK_SIZE", 0.05),
                "SEM_EXPIRY_DATE": _safe_str(r, "SEM_EXPIRY_DATE"),
                "SEM_STRIKE_PRICE": _safe_opt_float(r, "SEM_STRIKE_PRICE"),
                "SEM_OPTION_TYPE": _safe_opt_str(r, "SEM_OPTION_TYPE"),
                "SEM_CUSTOM_SYMBOL": _safe_opt_str(r, "SEM_CUSTOM_SYMBOL"),
                "SM_SYMBOL_NAME": _safe_opt_str(r, "SM_SYMBOL_NAME"),
            })
        return out


def _safe_float(r, col: str, default):
    """Safely get float value from row."""
    val = getattr(r, col, None)
    return val if pd.notna(val) else default


def _safe_str(r, col: str):
    """Safely get string value from row."""
    val = getattr(r, col, None)
    return str(val) if pd.notna(val) else None


def _safe_opt_float(r, col: str):
    """Safely get optional float value from row."""
    val = getattr(r, col, None)
    return val if pd.notna(val) else None


def _safe_opt_str(r, col: str):
    """Safely get optional string value from row."""
    val = getattr(r, col, None)
    return str(val) if pd.notna(val) else None
