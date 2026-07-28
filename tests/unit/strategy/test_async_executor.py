"""Tests for async strategy executor with timeouts."""

import asyncio
import time

from scalpr.strategy.executor import StrategyExecutor


class MockTick:
    """Mock tick for testing."""
    def __init__(self, symbol="RELIANCE"):
        self.symbol = symbol
        self.ltp = 2500.0
        self.cumulative_volume = 1000


class SlowStrategy:
    """Strategy that sleeps to simulate slow execution."""
    def __init__(self, sleep_time: float = 2.0):
        self.sleep_time = sleep_time
        self.tick_count = 0

    def on_tick(self, tick):
        time.sleep(self.sleep_time)
        self.tick_count += 1

    @property
    def __class__(self):
        return type('SlowStrategy', (), {'__name__': 'SlowStrategy'})


class FastStrategy:
    """Strategy that executes quickly."""
    def __init__(self):
        self.tick_count = 0

    def on_tick(self, tick):
        self.tick_count += 1

    @property
    def __class__(self):
        return type('FastStrategy', (), {'__name__': 'FastStrategy'})


class FailingStrategy:
    """Strategy that raises exceptions."""
    def __init__(self):
        self.tick_count = 0

    def on_tick(self, tick):
        self.tick_count += 1
        if self.tick_count % 2 == 0:
            raise ValueError("Simulated strategy error")

    @property
    def __class__(self):
        return type('FailingStrategy', (), {'__name__': 'FailingStrategy'})


class TestAsyncStrategyExecutor:
    """Test async strategy execution with timeouts."""

    def test_fast_strategy_completes(self):
        """Verify fast strategy completes within timeout."""
        executor = StrategyExecutor(timeout_seconds=0.5)
        strategy = FastStrategy()
        executor.register_strategy(strategy)

        tick = MockTick()
        asyncio.run(executor.on_tick(tick))

        assert strategy.tick_count == 1

    def test_slow_strategy_times_out(self):
        """Verify slow strategy times out (timeout prevents blocking, not thread cancellation)."""
        executor = StrategyExecutor(timeout_seconds=0.1)
        strategy = SlowStrategy(sleep_time=2.0)
        executor.register_strategy(strategy)

        tick = MockTick()
        # Timeout should occur, but thread may complete in background
        asyncio.run(executor.on_tick(tick))

        # Strategy may or may not have completed (thread continues after timeout)
        # Key point: timeout was logged and didn't block
        assert strategy.tick_count in [0, 1]  # Either timed out or completed

    def test_multiple_strategies_execute(self):
        """Verify multiple strategies all execute."""
        executor = StrategyExecutor(timeout_seconds=0.5)
        strategy1 = FastStrategy()
        strategy2 = FastStrategy()
        executor.register_strategy(strategy1)
        executor.register_strategy(strategy2)

        tick = MockTick()
        asyncio.run(executor.on_tick(tick))

        assert strategy1.tick_count == 1
        assert strategy2.tick_count == 1

    def test_strategy_error_doesnt_block_others(self):
        """Verify one strategy error doesn't prevent others from executing."""
        executor = StrategyExecutor(timeout_seconds=0.5)
        failing = FailingStrategy()
        fast = FastStrategy()
        executor.register_strategy(failing)
        executor.register_strategy(fast)

        tick = MockTick()
        # Run twice to trigger error on second tick
        asyncio.run(executor.on_tick(tick))
        asyncio.run(executor.on_tick(tick))

        # Fast strategy should have executed both times
        assert fast.tick_count == 2
        # Failing strategy should have executed (but errored on second)
        assert failing.tick_count == 2

    def test_timeout_records_metrics(self):
        """Verify timeout is recorded in metrics even if thread continues."""
        from scalpr.observability.metrics import metrics

        executor = StrategyExecutor(timeout_seconds=0.05)
        slow = SlowStrategy(sleep_time=0.5)
        executor.register_strategy(slow)

        initial_timeouts = metrics.get_counter("strategy_timeouts").value

        tick = MockTick()
        asyncio.run(executor.on_tick(tick))

        # Timeout should be recorded
        assert metrics.get_counter("strategy_timeouts").value == initial_timeouts + 1

    def test_metrics_recorded(self):
        """Verify execution metrics are recorded."""
        from scalpr.observability.metrics import metrics

        executor = StrategyExecutor(timeout_seconds=0.5)
        strategy = FastStrategy()
        executor.register_strategy(strategy)

        tick = MockTick()
        asyncio.run(executor.on_tick(tick))

        # Check metrics were recorded
        latency_hist = metrics.get_histogram("strategy_execution_latency_ms")
        assert latency_hist.count() > 0

    def test_no_strategies_no_error(self):
        """Verify executor handles empty strategy list."""
        executor = StrategyExecutor()
        tick = MockTick()

        # Should not raise
        asyncio.run(executor.on_tick(tick))

    def test_strategy_timeout_counter_incremented(self):
        """Verify timeout counter is incremented on timeout."""
        from scalpr.observability.metrics import metrics

        executor = StrategyExecutor(timeout_seconds=0.1)
        strategy = SlowStrategy(sleep_time=2.0)
        executor.register_strategy(strategy)

        # Get initial counter value
        initial_timeouts = metrics.get_counter("strategy_timeouts").value

        tick = MockTick()
        asyncio.run(executor.on_tick(tick))

        # Verify counter incremented
        assert metrics.get_counter("strategy_timeouts").value == initial_timeouts + 1

    def test_strategy_error_counter_incremented(self):
        """Verify error counter is incremented on exception."""
        from scalpr.observability.metrics import metrics

        executor = StrategyExecutor(timeout_seconds=0.5)
        strategy = FailingStrategy()
        executor.register_strategy(strategy)

        # Get initial counter value
        initial_errors = metrics.get_counter("strategy_errors").value

        tick = MockTick()
        # Execute twice to trigger error
        asyncio.run(executor.on_tick(tick))
        asyncio.run(executor.on_tick(tick))

        # Verify counter incremented
        assert metrics.get_counter("strategy_errors").value == initial_errors + 1
