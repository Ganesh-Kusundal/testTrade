from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"


@dataclass(slots=True, frozen=True)
class Signal:
    """Trading signal indicating setup detection."""
    symbol: str
    signal_type: SignalType
    price: Decimal
    timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.price, Decimal):
            raise TypeError("price must be a Decimal")


@dataclass(slots=True, frozen=True)
class Gate:
    """Signal generation filter gate status."""
    gate_id: str
    name: str
    passed: bool
    description: str = ""
