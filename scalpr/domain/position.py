from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import OrderSide
from scalpr.domain.values import ZERO


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class PositionState(str, Enum):
    FLAT = "FLAT"
    OPEN = "OPEN"
    REDUCING = "REDUCING"
    CLOSED = "CLOSED"
    REVERSED = "REVERSED"


@dataclass(slots=True, frozen=True)
class Position:
    """Position tracks open trading contract exposure, average entry, and PnL."""
    symbol: str
    exchange: Exchange
    quantity: int = 0
    avg_price: Decimal = ZERO
    ltp: Decimal = ZERO
    unrealised_pnl: Decimal = ZERO
    realised_pnl: Decimal = ZERO
    position_side: PositionSide = PositionSide.FLAT
    state: PositionState = PositionState.FLAT

    def __post_init__(self) -> None:
        if not isinstance(self.avg_price, Decimal):
            raise TypeError("avg_price must be a Decimal")
        if not isinstance(self.ltp, Decimal):
            raise TypeError("ltp must be a Decimal")
        if not isinstance(self.unrealised_pnl, Decimal):
            raise TypeError("unrealised_pnl must be a Decimal")
        if not isinstance(self.realised_pnl, Decimal):
            raise TypeError("realised_pnl must be a Decimal")
        if not isinstance(self.quantity, int):
            raise TypeError("quantity must be an integer")

    def with_ltp(self, ltp: Decimal) -> Position:
        """Mark-to-market position with updated LTP and return new Position copy."""
        if not isinstance(ltp, Decimal):
            raise TypeError("ltp must be a Decimal")

        if self.quantity > 0:
            unrealised = Decimal(self.quantity) * (ltp - self.avg_price)
        elif self.quantity < 0:
            unrealised = Decimal(abs(self.quantity)) * (self.avg_price - ltp)
        else:
            unrealised = ZERO

        return replace(self, ltp=ltp, unrealised_pnl=unrealised)

    def with_fill(self, quantity: int, price: Decimal, side: OrderSide) -> Position:
        """Calculate updated position state after applying a signed fill quantity."""
        self._validate_fill_params(quantity, price)

        old_qty = self.quantity
        delta = quantity
        new_qty = self._compute_new_quantity(old_qty, delta)

        new_avg, new_realised, new_state = self._compute_avg_realised_and_state(
            old_qty=old_qty,
            old_avg=self.avg_price,
            delta=delta,
            new_qty=new_qty,
            price=price,
            realised_pnl=self.realised_pnl,
            state=self.state,
        )

        new_side, new_state = self._resolve_side_and_state(
            new_qty=new_qty,
            current_state=self.state,
            new_state=new_state,
        )

        unrealised = self._compute_unrealised_pnl(new_qty, price, new_avg)

        return replace(
            self,
            quantity=new_qty,
            avg_price=new_avg,
            ltp=price,
            unrealised_pnl=unrealised,
            realised_pnl=new_realised,
            position_side=new_side,
            state=new_state,
        )

    def _validate_fill_params(self, quantity: int, price: Decimal) -> None:
        if not isinstance(price, Decimal):
            raise TypeError("price must be a Decimal")
        if not isinstance(quantity, int):
            raise TypeError("quantity must be an integer")

    @staticmethod
    def _compute_new_quantity(old_qty: int, delta: int) -> int:
        return old_qty + delta

    @staticmethod
    def _compute_avg_realised_and_state(
        old_qty: int,
        old_avg: Decimal,
        delta: int,
        new_qty: int,
        price: Decimal,
        realised_pnl: Decimal,
        state: PositionState,
    ) -> tuple[Decimal, Decimal, PositionState]:
        new_avg = old_avg
        new_realised = realised_pnl
        new_state = state

        if old_qty == 0:
            new_avg = price
        elif (old_qty > 0 and delta > 0) or (old_qty < 0 and delta < 0):
            new_avg = (Decimal(old_qty) * old_avg + Decimal(delta) * price) / Decimal(new_qty)
        else:
            closed = min(abs(old_qty), abs(delta))
            pnl_factor = Decimal("1") if old_qty > 0 else Decimal("-1")
            new_realised = realised_pnl + Decimal(closed) * (price - old_avg) * pnl_factor

            if new_qty == 0:
                new_avg = ZERO
                new_state = PositionState.CLOSED
            elif abs(delta) > abs(old_qty):
                new_avg = price
                new_state = PositionState.REVERSED
            else:
                new_avg = old_avg
                new_state = PositionState.REDUCING

        return new_avg, new_realised, new_state

    @staticmethod
    def _resolve_side_and_state(
        new_qty: int,
        current_state: PositionState,
        new_state: PositionState,
    ) -> tuple[PositionSide, PositionState]:
        if new_qty > 0:
            new_side = PositionSide.LONG
            if new_state == current_state:
                new_state = PositionState.OPEN
        elif new_qty < 0:
            new_side = PositionSide.SHORT
            if new_state == current_state:
                new_state = PositionState.OPEN
        else:
            new_side = PositionSide.FLAT
            new_state = PositionState.FLAT
        return new_side, new_state

    @staticmethod
    def _compute_unrealised_pnl(new_qty: int, price: Decimal, new_avg: Decimal) -> Decimal:
        if new_qty > 0:
            return Decimal(new_qty) * (price - new_avg)
        elif new_qty < 0:
            return Decimal(abs(new_qty)) * (new_avg - price)
        return ZERO

    def is_reducing(self, fill_side: OrderSide) -> bool:
        """Check if a fill would reduce this position's exposure."""
        if self.quantity == 0:
            return False
        if self.quantity > 0 and fill_side == OrderSide.SELL:
            return True
        return bool(self.quantity < 0 and fill_side == OrderSide.BUY)

    def notional_value(self) -> Decimal:
        """Return abs(quantity) * ltp as Decimal."""
        return Decimal(abs(self.quantity)) * self.ltp

    def total_pnl(self) -> Decimal:
        """Return total PnL (realised + unrealised)."""
        return self.realised_pnl + self.unrealised_pnl
