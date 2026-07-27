import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from scalpr.domain.tick import Tick, OHLCV
from scalpr.market_data.aggregator import TickAggregator, IST
from scalpr.market_data.historical import SeamStitcher
from scalpr.market_data.validators import TickValidator


@pytest.mark.asyncio
async def test_aggregator_mutates_last_candle_not_push_new():
    """TickAggregator mutates current candle for ticks within the same bar boundary."""
    agg = TickAggregator(timeframe_minutes=5)
    
    base_time = datetime(2026, 6, 23, 9, 15, 0, tzinfo=timezone.utc)
    
    # Tick 1: opens the bar
    t1 = Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 10, 10, base_time)
    res1 = await agg.process_tick(t1)
    assert res1 is None
    assert "RELIANCE" in agg.current_bars
    assert agg.current_bars["RELIANCE"].open == Decimal("2500.00")
    assert agg.current_bars["RELIANCE"].volume == 10
    
    # Tick 2: in same bar (9:17:00 IST is same 5m bar as 9:15:00 IST)
    t2 = Tick("RELIANCE", Decimal("2505.00"), Decimal("2504"), Decimal("2506"), 15, 25, base_time + timedelta(minutes=2))
    res2 = await agg.process_tick(t2)
    assert res2 is None
    assert agg.current_bars["RELIANCE"].close == Decimal("2505.00")
    assert agg.current_bars["RELIANCE"].high == Decimal("2505.00")
    assert agg.current_bars["RELIANCE"].volume == 25  # 10 + 15


@pytest.mark.asyncio
async def test_aggregator_rolls_over_at_bar_boundary():
    """TickAggregator rolls over to a new candle when tick crosses the bar boundary."""
    agg = TickAggregator(timeframe_minutes=5)
    base_time = datetime(2026, 6, 23, 9, 15, 0, tzinfo=timezone.utc)
    
    # Tick 1: opens the bar (9:15)
    t1 = Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 10, 10, base_time)
    await agg.process_tick(t1)
    
    # Tick 2: crosses the boundary to 9:20 (5 minutes later)
    t2 = Tick("RELIANCE", Decimal("2508.00"), Decimal("2507"), Decimal("2509"), 20, 30, base_time + timedelta(minutes=5))
    closed_bar = await agg.process_tick(t2)
    
    assert closed_bar is not None
    assert closed_bar.is_closed is True
    assert closed_bar.bar_open_time == base_time
    assert closed_bar.close == Decimal("2500.00")
    assert closed_bar.volume == 10
    
    # Check that new bar is open
    assert agg.current_bars["RELIANCE"].open == Decimal("2508.00")
    assert agg.current_bars["RELIANCE"].is_closed is False
    assert agg.current_bars["RELIANCE"].bar_open_time == base_time + timedelta(minutes=5)


def test_seam_stitcher_drops_ticks_before_history_end():
    """SeamStitcher drops any tick with exchange_timestamp <= history_end."""
    history_end = datetime(2026, 6, 23, 10, 0, 0, tzinfo=timezone.utc)
    stitcher = SeamStitcher(last_bar_timestamp=history_end)
    
    # Older tick
    t_old = Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 10, 10, history_end - timedelta(minutes=1))
    assert not stitcher.should_process_tick(t_old)
    
    # Same boundary tick
    t_same = Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 10, 10, history_end)
    assert not stitcher.should_process_tick(t_same)
    
    # Newer tick
    t_new = Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 10, 10, history_end + timedelta(seconds=1))
    assert stitcher.should_process_tick(t_new)


def test_validator_rejects_stale_tick():
    """TickValidator rejects a tick if exchange_timestamp is older than 5 seconds."""
    validator = TickValidator(staleness_threshold_seconds=5.0)
    
    # Fresh tick
    t_fresh = Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 10, 10, datetime.now(timezone.utc))
    assert validator.validate_tick(t_fresh)
    
    # Stale tick
    t_stale = Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 10, 10, datetime.now(timezone.utc) - timedelta(seconds=6))
    assert not validator.validate_tick(t_stale)


def test_validator_deduplicates_same_exchange_timestamp():
    """TickValidator rejects ticks with identical or older exchange_timestamp for same symbol."""
    validator = TickValidator()
    ts = datetime.now(timezone.utc)
    
    t1 = Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 10, 10, ts)
    t2 = Tick("RELIANCE", Decimal("2501.00"), Decimal("2500"), Decimal("2502"), 15, 25, ts)  # Same timestamp
    t3 = Tick("RELIANCE", Decimal("2502.00"), Decimal("2501"), Decimal("2503"), 5, 30, ts - timedelta(seconds=1)) # Older
    
    assert validator.validate_tick(t1)
    assert not validator.validate_tick(t2)
    assert not validator.validate_tick(t3)


@pytest.mark.asyncio
async def test_volume_delta_not_cumulative_in_ohlcv():
    """TickAggregator sums tick.delta_volume instead of using cumulative_volume in OHLCV volume."""
    agg = TickAggregator(timeframe_minutes=5)
    base_time = datetime.now(timezone.utc)
    
    t1 = Tick("RELIANCE", Decimal("2500.0"), Decimal("2499.0"), Decimal("2501.0"), 0, 1000, base_time)
    t2 = Tick("RELIANCE", Decimal("2505.0"), Decimal("2504.0"), Decimal("2506.0"), 25, 1025, base_time + timedelta(seconds=1))
    
    await agg.process_tick(t1)
    await agg.process_tick(t2)
    
    assert agg.current_bars["RELIANCE"].volume == 25
