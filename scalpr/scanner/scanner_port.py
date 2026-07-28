from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from scalpr.domain.instrument import Instrument


class IScanner(ABC):
    """Abstract Port representing the contract every contract scanner must satisfy."""

    @abstractmethod
    def scan(self, spot_price: Decimal, chain_data: list[dict[str, Any]]) -> list[Instrument]:
        """Scan a contract universe and return tradeable instruments, best first."""
        pass
