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
        if not isinstance(price, Decimal):
            raise TypeError("price must be a Decimal")
        if not isinstance(quantity, int):
            raise TypeError("quantity must be an integer")

        old_qty = self.quantity
        old_avg = self.avg_price
        delta = quantity
        new_qty = old_qty + delta

        # Defaults
        new_avg = old_avg
        new_realised = self.realised_pnl
        new_state = self.state

        if old_qty == 0:
            new_avg = price
        elif (old_qty > 0 and delta > 0) or (old_qty < 0 and delta < 0):
            # Adding to position
            new_avg = (Decimal(old_qty) * old_avg + Decimal(delta) * price) / Decimal(new_qty)
        else:
            # Reducing position or reversing position
            closed = min(abs(old_qty), abs(delta))
            pnl_factor = Decimal("1") if old_qty > 0 else Decimal("-1")
            new_realised = self.realised_pnl + Decimal(closed) * (price - old_avg) * pnl_factor

            if new_qty == 0:
                new_avg = ZERO
                new_state = PositionState.CLOSED
            elif abs(delta) > abs(old_qty):
                # Position reversed
                new_avg = price
                new_state = PositionState.REVERSED
            else:
                # Position reduced but same side remains
                new_avg = old_avg
                new_state = PositionState.REDUCING

        # Determine PositionSide
        if new_qty > 0:
            new_side = PositionSide.LONG
            if new_state == self.state:
                new_state = PositionState.OPEN
        elif new_qty < 0:
            new_side = PositionSide.SHORT
            if new_state == self.state:
                new_state = PositionState.OPEN
        else:
            new_side = PositionSide.FLAT
            new_state = PositionState.FLAT

        # Calculate unrealised PnL at the fill price (as new LTP)
        if new_qty > 0:
            unrealised = Decimal(new_qty) * (price - new_avg)
        elif new_qty < 0:
            unrealised = Decimal(abs(new_qty)) * (new_avg - price)
        else:
            unrealised = ZERO

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
