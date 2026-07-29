"""Comprehensive tests for SessionGuard timezone logic bug fix."""

from datetime import datetime
from decimal import Decimal

import pytest

from scalpr.risk.session_guard import IST, SessionGuard
from scalpr.simulation.simulated_gateway import SimulatedGateway


class TestSessionGuardNSE:
    """Test NSE market cutoff logic (15:00-15:30 IST window)."""

    def _make_time(self, hour: int, minute: int) -> datetime:
        """Create a datetime in IST timezone."""
        return datetime(2024, 1, 15, hour, minute, 0, tzinfo=IST)

    def test_warning_fires_at_15_00(self):
        """Verify warning fires once at 15:00 IST."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(15, 0)
        result = guard.check_market_cutoff(current_time)

        assert result is False  # Not halted yet
        assert guard._warned_nse is True

    def test_warning_fires_only_once(self):
        """Verify warning does not fire again at 15:05."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        # First call at 15:00
        guard.check_market_cutoff(self._make_time(15, 0))
        assert guard._warned_nse is True

        # Second call at 15:05 - should not warn again
        guard.check_market_cutoff(self._make_time(15, 5))
        assert guard._warned_nse is True  # Still True, no duplicate warning

    def test_square_off_fires_at_15_15(self):
        """Verify square-off fires at exactly 15:15 IST."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(15, 15)
        result = guard.check_market_cutoff(current_time)

        assert result is True  # Halted
        assert guard.halted is True

    def test_square_off_fires_at_15_16(self):
        """Verify square-off fires at 15:16 IST (after cutoff)."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(15, 16)
        result = guard.check_market_cutoff(current_time)

        assert result is True
        assert guard.halted is True

    def test_square_off_fires_at_15_30(self):
        """Verify square-off fires at 15:30 IST (well after cutoff)."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(15, 30)
        result = guard.check_market_cutoff(current_time)

        assert result is True
        assert guard.halted is True

    def test_no_action_before_15_00(self):
        """Verify no warning or square-off before 15:00."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(14, 59)
        result = guard.check_market_cutoff(current_time)

        assert result is False
        assert guard._warned_nse is False
        assert guard.halted is False

    def test_warning_fires_at_15_14(self):
        """Verify warning still fires at 15:14 (last minute before cutoff)."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(15, 14)
        result = guard.check_market_cutoff(current_time)

        # Warning should fire (but not square-off yet)
        assert guard._warned_nse is True
        assert result is False  # Not halted at 15:14

    def test_warning_and_cutoff_sequence(self):
        """Test full sequence: warning at 15:00, cutoff at 15:15."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        # 15:00 - Warning
        guard.check_market_cutoff(self._make_time(15, 0))
        assert guard._warned_nse is True
        assert guard.halted is False

        # 15:10 - Still waiting
        guard.check_market_cutoff(self._make_time(15, 10))
        assert guard.halted is False

        # 15:15 - Cutoff
        result = guard.check_market_cutoff(self._make_time(15, 15))
        assert result is True
        assert guard.halted is True

    @pytest.mark.parametrize("minute", [0, 1, 5, 10, 14])
    def test_warning_window_minutes(self, minute):
        """Test all minutes in warning window (15:00-15:14)."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(15, minute)
        guard.check_market_cutoff(current_time)

        assert guard._warned_nse is True
        assert guard.halted is False

    @pytest.mark.parametrize("minute", [15, 16, 20, 25, 30, 45, 59])
    def test_cutoff_window_minutes(self, minute):
        """Test all minutes in cutoff window (15:15+)."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(15, minute)
        result = guard.check_market_cutoff(current_time)

        assert result is True
        assert guard.halted is True


class TestSessionGuardMCX:
    """Test MCX market cutoff logic (23:00-23:30 IST window)."""

    def _make_time(self, hour: int, minute: int) -> datetime:
        """Create a datetime in IST timezone."""
        return datetime(2024, 1, 15, hour, minute, 0, tzinfo=IST)

    def test_warning_fires_at_23_00(self):
        """Verify warning fires once at 23:00 IST."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(23, 0)
        result = guard.check_market_cutoff(current_time)

        assert result is False
        assert guard._warned_mcx is True

    def test_warning_fires_only_once(self):
        """Verify warning does not fire again at 23:05."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        # First call at 23:00
        guard.check_market_cutoff(self._make_time(23, 0))
        assert guard._warned_mcx is True

        # Second call at 23:05
        guard.check_market_cutoff(self._make_time(23, 5))
        assert guard._warned_mcx is True

    def test_square_off_fires_at_23_15(self):
        """Verify square-off fires at exactly 23:15 IST."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(23, 15)
        result = guard.check_market_cutoff(current_time)

        assert result is True
        assert guard.halted is True

    def test_square_off_fires_at_23_16(self):
        """Verify square-off fires at 23:16 IST."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(23, 16)
        result = guard.check_market_cutoff(current_time)

        assert result is True
        assert guard.halted is True

    def test_no_action_before_23_00(self):
        """Verify no action before 23:00."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(22, 59)
        result = guard.check_market_cutoff(current_time)

        assert result is False
        assert guard._warned_mcx is False
        assert guard.halted is False

    @pytest.mark.parametrize("minute", [0, 1, 5, 10, 14])
    def test_warning_window_minutes(self, minute):
        """Test all minutes in MCX warning window (23:00-23:14)."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(23, minute)
        guard.check_market_cutoff(current_time)

        assert guard._warned_mcx is True
        assert guard.halted is False

    @pytest.mark.parametrize("minute", [15, 16, 20, 30, 45])
    def test_cutoff_window_minutes(self, minute):
        """Test all minutes in MCX cutoff window (23:15+)."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        current_time = self._make_time(23, minute)
        result = guard.check_market_cutoff(current_time)

        assert result is True
        assert guard.halted is True


class TestSessionGuardReset:
    """Test SessionGuard reset functionality."""

    def test_reset_clears_warnings(self):
        """Verify reset clears warning flags."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        # Trigger warnings
        guard.check_market_cutoff(datetime(2024, 1, 15, 15, 0, tzinfo=IST))
        guard.check_market_cutoff(datetime(2024, 1, 15, 23, 0, tzinfo=IST))

        assert guard._warned_nse is True
        assert guard._warned_mcx is True

        # Reset
        guard.reset_guard()

        assert guard._warned_nse is False
        assert guard._warned_mcx is False

    def test_reset_clears_halt(self):
        """Verify reset clears halt state."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        # Trigger halt
        guard.check_market_cutoff(datetime(2024, 1, 15, 15, 15, tzinfo=IST))
        assert guard.halted is True

        # Reset
        guard.reset_guard()
        assert guard.halted is False

    def test_reset_clears_consecutive_losses(self):
        """Verify reset clears loss counter."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        # Record losses
        guard.record_pnl(Decimal("-100"))
        guard.record_pnl(Decimal("-200"))
        assert guard.consecutive_losses == 2

        # Reset
        guard.reset_guard()
        assert guard.consecutive_losses == 0


class TestSessionGuardConsecutiveLosses:
    """Test consecutive loss tracking."""

    def test_three_losses_trigger_halt(self):
        """Verify 3 consecutive losses trigger square-off."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        guard.record_pnl(Decimal("-100"))
        guard.record_pnl(Decimal("-200"))
        guard.record_pnl(Decimal("-300"))

        assert guard.halted is True
        assert guard.consecutive_losses == 3

    def test_profit_resets_counter(self):
        """Verify profit resets consecutive loss counter."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        guard.record_pnl(Decimal("-100"))
        guard.record_pnl(Decimal("-200"))
        guard.record_pnl(Decimal("+150"))  # Profit

        assert guard.consecutive_losses == 0
        assert guard.halted is False

    def test_zero_pnl_resets_counter(self):
        """Verify zero PnL resets counter (not a loss)."""
        gateway = SimulatedGateway(starting_capital=Decimal("100000"))
        guard = SessionGuard(gateway)

        guard.record_pnl(Decimal("-100"))
        guard.record_pnl(Decimal("0"))  # Zero PnL is not a loss

        # Counter should reset (0 is not < 0)
        assert guard.consecutive_losses == 0
