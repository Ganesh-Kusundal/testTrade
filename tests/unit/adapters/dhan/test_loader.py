from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from scalpr.adapters.dhan._loader import InstrumentLoader


class TestInstrumentLoaderCacheDir:
    def test_default_cache_dir(self):
        loader = InstrumentLoader()
        expected = Path(__file__).resolve().parents[4] / "runtime-dev" / "instruments"
        assert loader._cache_dir == expected

    def test_custom_cache_dir_str(self):
        loader = InstrumentLoader(cache_dir="/tmp/my_instruments")
        assert loader._cache_dir == Path("/tmp/my_instruments")

    def test_custom_cache_dir_path(self):
        loader = InstrumentLoader(cache_dir=Path("/tmp/my_instruments"))
        assert loader._cache_dir == Path("/tmp/my_instruments")

    def test_constant_url(self):
        assert InstrumentLoader.INSTRUMENT_CSV_URL == "https://images.dhan.co/api-data/api-scrip-master.csv"


class TestInstrumentLoaderCachedPath:
    def test_none_when_no_cache(self, tmp_path: Path):
        loader = InstrumentLoader(cache_dir=tmp_path)
        assert loader.cached_path() is None

    def test_none_when_empty_file(self, tmp_path: Path):
        today = date.today().isoformat()
        p = tmp_path / f"instruments_{today}.csv"
        p.touch()
        loader = InstrumentLoader(cache_dir=tmp_path)
        assert loader.cached_path() is None

    def test_returns_path_when_cache_exists(self, tmp_path: Path):
        today = date.today().isoformat()
        p = tmp_path / f"instruments_{today}.csv"
        p.write_text("a,b\n1,2\n")
        loader = InstrumentLoader(cache_dir=tmp_path)
        result = loader.cached_path()
        assert result == p

    def test_ignores_old_dates(self, tmp_path: Path):
        old = tmp_path / "instruments_2020-01-01.csv"
        old.write_text("a,b\n1,2\n")
        loader = InstrumentLoader(cache_dir=tmp_path)
        assert loader.cached_path() is None


class TestInstrumentLoaderEnsureLoaded:
    def test_returns_cached_path_when_exists(self, tmp_path: Path):
        today = date.today().isoformat()
        p = tmp_path / f"instruments_{today}.csv"
        p.write_text("a,b\n1,2\n")
        loader = InstrumentLoader(cache_dir=tmp_path)
        result = loader.ensure_loaded()
        assert result == p

    def test_downloads_when_no_cache(self, tmp_path: Path):
        today = date.today().isoformat()
        loader = InstrumentLoader(cache_dir=tmp_path)
        with patch.object(loader, "download_instruments") as mock_dl:
            mock_dl.return_value = tmp_path / f"instruments_{today}.csv"
            result = loader.ensure_loaded()
        mock_dl.assert_called_once_with()
        assert result.name == f"instruments_{today}.csv"

    def test_force_download_triggers_download(self, tmp_path: Path):
        today = date.today().isoformat()
        p = tmp_path / f"instruments_{today}.csv"
        p.write_text("a,b\n1,2\n")
        loader = InstrumentLoader(cache_dir=tmp_path)
        with patch.object(loader, "download_instruments") as mock_dl:
            mock_dl.return_value = p
            loader.ensure_loaded(force_download=True)
        mock_dl.assert_called_once_with()

    def test_creates_cache_dir(self, tmp_path: Path):
        d = tmp_path / "nonexistent" / "subdir"
        loader = InstrumentLoader(cache_dir=d)
        with patch.object(loader, "download_instruments") as mock_dl:
            mock_dl.return_value = d / f"instruments_{date.today().isoformat()}.csv"
            loader.ensure_loaded()
        assert d.exists()

    def test_calls_cleanup(self, tmp_path: Path):
        today = date.today().isoformat()
        p = tmp_path / f"instruments_{today}.csv"
        p.write_text("a,b\n1,2\n")
        loader = InstrumentLoader(cache_dir=tmp_path)
        with patch.object(loader, "cleanup_old_cache") as mock_clean:
            loader.ensure_loaded()
        mock_clean.assert_called_once_with()

    def test_download_error_no_cache_raises(self, tmp_path: Path):
        loader = InstrumentLoader(cache_dir=tmp_path)
        with patch.object(loader, "download_instruments") as mock_dl:
            mock_dl.side_effect = OSError("network error")
            with pytest.raises(IOError, match="network error"):
                loader.ensure_loaded()

    def test_multiple_calls_reuse_cache(self, tmp_path: Path):
        today = date.today().isoformat()
        p = tmp_path / f"instruments_{today}.csv"
        p.write_text("a,b\n1,2\n")
        loader = InstrumentLoader(cache_dir=tmp_path)
        with patch.object(loader, "download_instruments") as mock_dl:
            loader.ensure_loaded()
            loader.ensure_loaded()
            loader.ensure_loaded()
        mock_dl.assert_not_called()


class TestInstrumentLoaderDownload:
    def test_downloads_from_correct_url(self, tmp_path: Path):
        loader = InstrumentLoader(cache_dir=tmp_path)
        csv_content = "a,b\n1,2\n"
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = csv_content.encode()
        with patch("scalpr.adapters.dhan._loader.requests.get", return_value=mock_resp) as mock_get:
            loader.download_instruments()
        mock_get.assert_called_once_with(
            "https://images.dhan.co/api-data/api-scrip-master.csv", timeout=120
        )

    def test_saves_to_correct_path(self, tmp_path: Path):
        loader = InstrumentLoader(cache_dir=tmp_path)
        today = date.today().isoformat()
        csv_content = "a,b\n1,2\n"
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = csv_content.encode()
        with patch("scalpr.adapters.dhan._loader.requests.get", return_value=mock_resp):
            result = loader.download_instruments()
        expected = tmp_path / f"instruments_{today}.csv"
        assert result == expected
        assert expected.exists()
        assert expected.read_text() == csv_content

    def test_atomic_replace_no_partial_file_on_success(self, tmp_path: Path):
        loader = InstrumentLoader(cache_dir=tmp_path)
        csv_content = "a,b\n1,2\n"
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = csv_content.encode()
        with patch("scalpr.adapters.dhan._loader.requests.get", return_value=mock_resp):
            loader.download_instruments()
        today = date.today().isoformat()
        tmp_file = tmp_path / f"instruments_{today}.csv.tmp"
        assert not tmp_file.exists()

    def test_removes_tmp_on_http_error(self, tmp_path: Path):
        loader = InstrumentLoader(cache_dir=tmp_path)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.raise_for_status.side_effect = requests.HTTPError("401")
        mock_resp.content = b""
        with (
            patch("scalpr.adapters.dhan._loader.requests.get", return_value=mock_resp),
            pytest.raises(requests.HTTPError),
        ):
            loader.download_instruments()
        assert not list(tmp_path.glob("*.csv.tmp"))

    def test_raises_on_network_error(self, tmp_path: Path):
        loader = InstrumentLoader(cache_dir=tmp_path)
        with patch("scalpr.adapters.dhan._loader.requests.get", side_effect=requests.ConnectionError("no net")):
            with pytest.raises(requests.ConnectionError):
                loader.download_instruments()

    def test_removes_tmp_on_network_error(self, tmp_path: Path):
        loader = InstrumentLoader(cache_dir=tmp_path)
        with patch("scalpr.adapters.dhan._loader.requests.get", side_effect=requests.ConnectionError("no net")):
            with pytest.raises(requests.ConnectionError):
                loader.download_instruments()
        assert not list(tmp_path.glob("*.csv.tmp"))

    def test_writes_csv_content(self, tmp_path: Path):
        loader = InstrumentLoader(cache_dir=tmp_path)
        csv_content = "SYMBOL,PRICE\nNIFTY,19500\nBANKNIFTY,44000\n"
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.raise_for_status.return_value = None
        mock_resp.content = csv_content.encode()
        with patch("scalpr.adapters.dhan._loader.requests.get", return_value=mock_resp):
            result = loader.download_instruments()
        assert result.read_text() == csv_content


class TestInstrumentLoaderCleanup:
    def test_deletes_old_files(self, tmp_path: Path):
        old = tmp_path / "instruments_2020-01-01.csv"
        old.write_text("a,b\n1,2\n")
        old_mtime = 1000000
        import os
        os.utime(old, (old_mtime, old_mtime))
        loader = InstrumentLoader(cache_dir=tmp_path)
        loader.cleanup_old_cache(days=1)
        assert not old.exists()

    def test_keeps_recent_files(self, tmp_path: Path):
        today = date.today().isoformat()
        p = tmp_path / f"instruments_{today}.csv"
        p.write_text("a,b\n1,2\n")
        loader = InstrumentLoader(cache_dir=tmp_path)
        loader.cleanup_old_cache(days=7)
        assert p.exists()

    def test_keeps_recent_files_custom_days(self, tmp_path: Path):
        recent = tmp_path / "instruments_2025-01-01.csv"
        recent.write_text("a,b\n1,2\n")
        import time
        recent_mtime = time.time() - (2 * 24 * 3600)
        import os
        os.utime(recent, (recent_mtime, recent_mtime))
        loader = InstrumentLoader(cache_dir=tmp_path)
        loader.cleanup_old_cache(days=7)
        assert recent.exists()

    def test_deletes_files_older_than_custom_days(self, tmp_path: Path):
        old = tmp_path / "instruments_2020-01-01.csv"
        old.write_text("a,b\n1,2\n")
        old_mtime = 1000000
        import os
        os.utime(old, (old_mtime, old_mtime))
        loader = InstrumentLoader(cache_dir=tmp_path)
        loader.cleanup_old_cache(days=100)
        assert not old.exists()

    def test_handles_missing_directory(self, tmp_path: Path):
        d = tmp_path / "does_not_exist_yet"
        loader = InstrumentLoader(cache_dir=d)
        loader.cleanup_old_cache()

    def test_ignores_non_cache_csv_files(self, tmp_path: Path):
        other = tmp_path / "data.csv"
        other.write_text("a,b\n1,2\n")
        loader = InstrumentLoader(cache_dir=tmp_path)
        loader.cleanup_old_cache(days=0)
        assert other.exists()

    def test_does_not_raise_on_permission_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(Path, "glob", MagicMock(side_effect=PermissionError("denied")))
        loader = InstrumentLoader(cache_dir=tmp_path)
        loader.cleanup_old_cache()
