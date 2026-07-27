"""SessionGuard must not call square_off_all more than once per cutoff."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from decimal import Decimal
from scalpr.risk.session_guard import SessionGuard

IST = timezone(timedelta(hours=5, minutes=30))


def test_cutoff_should_only_square_off_once():
    """check_market_cutoff called multiple times after 15:15 must only square off once."""
    mock_gateway = MagicMock()
    guard = SessionGuard(gateway=mock_gateway, max_losses=3)

    # 15:20 IST — past NSE cutoff
    cutoff_time = datetime(2026, 7, 27, 15, 20, tzinfo=IST)

    guard.check_market_cutoff(cutoff_time)
    guard.check_market_cutoff(cutoff_time)
    guard.check_market_cutoff(cutoff_time)

    mock_gateway.square_off_all.assert_called_once()


def test_mcx_cutoff_should_only_square_off_once():
    """check_market_cutoff called multiple times after 23:15 must only square off once."""
    mock_gateway = MagicMock()
    guard = SessionGuard(gateway=mock_gateway, max_losses=3)

    cutoff_time = datetime(2026, 7, 27, 23, 20, tzinfo=IST)

    guard.check_market_cutoff(cutoff_time)
    guard.check_market_cutoff(cutoff_time)

    mock_gateway.square_off_all.assert_called_once()
