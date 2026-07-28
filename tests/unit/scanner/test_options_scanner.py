"""Edge-case tests for OptionsScanner — div-by-zero guard."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from scalpr.scanner.options_scanner import OptionsScanner


def _chain_row(strike: str, **overrides):
    base = {
        "symbol": "",
        "security_id": 99999,
        "strike": Decimal(strike),
        "bid": Decimal("10"),
        "ask": Decimal("11"),
        "oi": 5000,
        "volume": 10000,
        "delta": None,
    }
    base.update(overrides)
    return base


class TestScannerZeroSpotGuard:
    def test_zero_spot_price_returns_empty_without_dividing(self):
        resolver = MagicMock()
        scanner = OptionsScanner(resolver)
        chain = [_chain_row("24000")]
        # Must NOT raise ZeroDivisionError; must return []
        assert scanner.scan(Decimal("0"), chain) == []
        # And must not even attempt to resolve anything
        resolver.get_by_security_id.assert_not_called()
        resolver.resolve.assert_not_called()

    def test_negative_spot_price_returns_empty(self):
        resolver = MagicMock()
        scanner = OptionsScanner(resolver)
        assert scanner.scan(Decimal("-1"), [_chain_row("24000")]) == []

    def test_positive_spot_price_still_resolves_normally(self):
        resolver = MagicMock()
        inst = MagicMock()
        resolver.get_by_security_id.return_value = inst
        scanner = OptionsScanner(resolver, min_oi=1, min_volume=1, max_spread=Decimal("5"))
        picks = scanner.scan(Decimal("24000"), [_chain_row("24000")])
        assert picks == [inst]
