"""SessionGuard must not call square_off_all more than once per cutoff."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from scalpr.risk.session_guard import SessionGuard
from scalpr.simulation.simulated_gateway import SimulatedGateway

IST = timezone(timedelta(hours=5, minutes=30))


def test_cutoff_should_only_square_off_once():
    """check_market_cutoff called multiple times after 15:15 must only square off once."""
    gateway = SimulatedGateway(starting_capital=Decimal("100000"))
    guard = SessionGuard(gateway=gateway, max_losses=3)

    # 15:20 IST — past NSE cutoff
    cutoff_time = datetime(2026, 7, 27, 15, 20, tzinfo=IST)

    guard.check_market_cutoff(cutoff_time)
    guard.check_market_cutoff(cutoff_time)
    guard.check_market_cutoff(cutoff_time)

    assert guard._squared_off_nse
    assert guard.halted


def test_mcx_cutoff_should_only_square_off_once():
    """check_market_cutoff called multiple times after 23:15 must only square off once."""
    gateway = SimulatedGateway(starting_capital=Decimal("100000"))
    guard = SessionGuard(gateway=gateway, max_losses=3)

    cutoff_time = datetime(2026, 7, 27, 23, 20, tzinfo=IST)

    guard.check_market_cutoff(cutoff_time)
    guard.check_market_cutoff(cutoff_time)

    assert guard._squared_off_mcx
    assert guard.halted
