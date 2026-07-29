"""Unit tests for TOTP cooldown guard."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from scalpr.brokers.dhan._totp_cooldown import (
    TotpCooldownGuard,
    TotpRateLimitError,
)


@pytest.fixture(autouse=True)
def _reset_singletons():
    TotpCooldownGuard.reset_instances()
    yield
    TotpCooldownGuard.reset_instances()


class TestTotpCooldownGuard:
    def test_first_attempt_allowed(self, tmp_path: Path):
        guard = TotpCooldownGuard("dhan", state_path=tmp_path / "cooldown.json")
        guard.check_allowed()  # should not raise

    def test_second_attempt_within_cooldown_raises(self, tmp_path: Path):
        guard = TotpCooldownGuard("dhan", cooldown_seconds=120, state_path=tmp_path / "cooldown.json")
        guard.record_attempt()
        with pytest.raises(TotpRateLimitError, match="cooldown active"):
            guard.check_allowed()

    def test_remaining_cooldown_decreases(self, tmp_path: Path):
        guard = TotpCooldownGuard("dhan", cooldown_seconds=10, state_path=tmp_path / "cooldown.json")
        guard.record_attempt()
        remaining = guard.remaining_cooldown_seconds()
        assert 8 < remaining <= 10

    def test_cooldown_expired_allows_attempt(self, tmp_path: Path):
        guard = TotpCooldownGuard("dhan", cooldown_seconds=0.1, state_path=tmp_path / "cooldown.json")
        guard.record_attempt()
        time.sleep(0.15)
        guard.check_allowed()  # should not raise

    def test_record_success_updates_state(self, tmp_path: Path):
        guard = TotpCooldownGuard("dhan", state_path=tmp_path / "cooldown.json")
        guard.record_success()
        data = json.loads((tmp_path / "cooldown.json").read_text())
        assert data["last_success_at"] is not None
        assert data["last_attempt_at"] is not None

    def test_record_rate_limited_resets_cooldown(self, tmp_path: Path):
        guard = TotpCooldownGuard("dhan", cooldown_seconds=120, state_path=tmp_path / "cooldown.json")
        guard.record_rate_limited()
        remaining = guard.remaining_cooldown_seconds()
        assert remaining > 100

    def test_persistence_across_instances(self, tmp_path: Path):
        path = tmp_path / "cooldown.json"
        guard1 = TotpCooldownGuard("dhan", cooldown_seconds=120, state_path=path)
        guard1.record_attempt()

        TotpCooldownGuard.reset_instances()
        guard2 = TotpCooldownGuard("dhan", cooldown_seconds=120, state_path=path)
        with pytest.raises(TotpRateLimitError):
            guard2.check_allowed()

    def test_singleton_per_broker(self, tmp_path: Path):
        g1 = TotpCooldownGuard.for_broker("dhan")
        g2 = TotpCooldownGuard.for_broker("dhan")
        assert g1 is g2

    def test_rate_limit_error_has_remaining(self):
        err = TotpRateLimitError("test", remaining_seconds=42.0)
        assert err.remaining_seconds == 42.0
        assert "test" in str(err)

    def test_corrupt_state_file_ignored(self, tmp_path: Path):
        path = tmp_path / "cooldown.json"
        path.write_text("not json")
        guard = TotpCooldownGuard("dhan", state_path=path)
        guard.check_allowed()  # should not raise — corrupt state treated as fresh
