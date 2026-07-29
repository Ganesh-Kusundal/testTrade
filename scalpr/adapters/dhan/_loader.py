from __future__ import annotations

import logging
import os
import time
from datetime import date
from pathlib import Path

import requests

from config.endpoints import Dhan

logger = logging.getLogger(__name__)


class InstrumentLoader:
    INSTRUMENT_CSV_URL: str = Dhan.INSTRUMENT_CSV

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        if cache_dir is None:
            cache_dir = Path(__file__).resolve().parents[3] / "runtime-dev" / "instruments"
        self._cache_dir = Path(cache_dir)

    def ensure_loaded(self, force_download: bool = False) -> Path:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self.cleanup_old_cache()

        cached = self.cached_path()
        if cached is not None and not force_download:
            logger.info("Instrument cache hit: %s", cached)
            return cached

        return self.download_instruments()

    def download_instruments(self) -> Path:
        url = self.INSTRUMENT_CSV_URL
        logger.info("Downloading instruments from %s", url)

        self._cache_dir.mkdir(parents=True, exist_ok=True)

        today = date.today()
        cache_path = self._cache_dir / f"instruments_{today.isoformat()}.csv"
        tmp_path = cache_path.with_suffix(".csv.tmp")

        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            tmp_path.write_bytes(resp.content)
            os.replace(tmp_path, cache_path)
            logger.info("Instruments saved to %s", cache_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

        return cache_path

    def cached_path(self) -> Path | None:
        today = date.today()
        path = self._cache_dir / f"instruments_{today.isoformat()}.csv"
        if path.exists() and path.stat().st_size > 0:
            return path
        return None

    def cleanup_old_cache(self, days: int = 7) -> None:
        now = time.time()
        cutoff = now - (days * 24 * 3600)
        try:
            for path in self._cache_dir.glob("instruments_*.csv"):
                if path.is_file() and path.stat().st_mtime < cutoff:
                    logger.info("Removing old cache: %s", path)
                    path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Cache cleanup failed: %s", exc)
