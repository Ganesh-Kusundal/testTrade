"""Tests for observability foundation (metrics, logging, tracing)."""

import json
import logging

from scalpr.observability.logging import JsonFormatter
from scalpr.observability.metrics import (
    CounterMetric,
    GaugeMetric,
    HistogramMetric,
    MetricsRegistry,
)
from scalpr.observability.tracing import TraceContext


class TestCounterMetric:
    """Test counter metric functionality."""

    def test_increment(self):
        counter = CounterMetric("test_counter")
        counter.increment()
        assert counter.value == 1

    def test_increment_by_amount(self):
        counter = CounterMetric("test_counter")
        counter.increment(5)
        assert counter.value == 5

    def test_multiple_increments(self):
        counter = CounterMetric("test_counter")
        counter.increment()
        counter.increment()
        counter.increment(3)
        assert counter.value == 5


class TestHistogramMetric:
    """Test histogram metric functionality."""

    def test_observe(self):
        hist = HistogramMetric("test_hist")
        hist.observe(10.0)
        assert len(hist.values) == 1
        assert hist.values[0] == 10.0

    def test_p50_odd_count(self):
        hist = HistogramMetric("test_hist")
        for val in [10, 20, 30, 40, 50]:
            hist.observe(float(val))

        assert hist.p50() == 30.0

    def test_p50_even_count(self):
        hist = HistogramMetric("test_hist")
        for val in [10, 20, 30, 40]:
            hist.observe(float(val))

        # p50 for even count: index = 4 // 2 = 2 (0-indexed)
        assert hist.p50() == 30.0

    def test_p99(self):
        hist = HistogramMetric("test_hist")
        for i in range(100):
            hist.observe(float(i))

        # p99 should be 99th value
        assert hist.p99() == 99.0

    def test_empty_histogram(self):
        hist = HistogramMetric("test_hist")
        assert hist.p50() == 0.0
        assert hist.p99() == 0.0

    def test_count(self):
        hist = HistogramMetric("test_hist")
        hist.observe(10.0)
        hist.observe(20.0)
        assert hist.count() == 2


class TestGaugeMetric:
    """Test gauge metric functionality."""

    def test_set(self):
        gauge = GaugeMetric("test_gauge")
        gauge.set(42.0)
        assert gauge.value == 42.0

    def test_override(self):
        gauge = GaugeMetric("test_gauge")
        gauge.set(10.0)
        gauge.set(20.0)
        assert gauge.value == 20.0


class TestMetricsRegistry:
    """Test metrics registry functionality."""

    def test_register_counter(self):
        registry = MetricsRegistry()
        counter = registry.register_counter("test_counter", "Test counter")
        assert counter.name == "test_counter"
        assert counter.description == "Test counter"

    def test_get_counter(self):
        registry = MetricsRegistry()
        registry.register_counter("test_counter")
        counter = registry.get_counter("test_counter")
        assert counter is not None
        assert counter.name == "test_counter"

    def test_counter_persistence(self):
        """Test that counter values persist across get calls."""
        registry = MetricsRegistry()
        registry.register_counter("test_counter")

        counter1 = registry.get_counter("test_counter")
        counter1.increment(5)

        counter2 = registry.get_counter("test_counter")
        assert counter2.value == 5

    def test_snapshot(self):
        registry = MetricsRegistry()

        # Add some data
        registry.get_counter("orders_submitted").increment(10)
        registry.get_histogram("order_routing_latency_ms").observe(5.0)
        registry.get_gauge("active_positions").set(3.0)

        snapshot = registry.snapshot()

        assert "counters" in snapshot
        assert "histograms" in snapshot
        assert "gauges" in snapshot
        assert "timestamp" in snapshot

        assert snapshot["counters"]["orders_submitted"] == 10
        assert snapshot["histograms"]["order_routing_latency_ms"]["count"] == 1
        assert snapshot["gauges"]["active_positions"] == 3.0

    def test_core_metrics_initialized(self):
        """Test that core trading metrics are initialized on startup."""
        registry = MetricsRegistry()

        # Verify counters
        assert registry.get_counter("orders_submitted") is not None
        assert registry.get_counter("strategy_ticks") is not None
        assert registry.get_counter("strategy_errors") is not None

        # Verify histograms
        assert registry.get_histogram("order_routing_latency_ms") is not None
        assert registry.get_histogram("tick_processing_latency_ms") is not None

        # Verify gauges
        assert registry.get_gauge("active_positions") is not None
        assert registry.get_gauge("circuit_breaker_state") is not None


class TestJsonFormatter:
    """Test JSON log formatter."""

    def test_format_basic(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        log_entry = json.loads(output)

        assert log_entry["message"] == "Test message"
        assert log_entry["level"] == "INFO"
        assert log_entry["service"] == "scalpr"
        assert "timestamp" in log_entry

    def test_format_with_correlation_id(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        # New formatter uses correlation_id instead of trace_id
        record.correlation_id = "abc12345"
        record.request_id = "req-123"

        output = formatter.format(record)
        log_entry = json.loads(output)

        assert log_entry["correlation_id"] == "abc12345"
        assert log_entry["request_id"] == "req-123"


class TestTraceContext:
    """Test trace context functionality."""

    def test_start_creates_context(self):
        ctx = TraceContext.start("RELIANCE-EQ")

        assert ctx.symbol == "RELIANCE-EQ"
        assert ctx.trace_id is not None
        assert ctx.tick_id is not None
        assert ctx.start_time is not None

    def test_trace_id_is_short(self):
        """Trace ID should be first 8 chars of UUID."""
        ctx = TraceContext.start("RELIANCE-EQ")

        assert len(ctx.trace_id) == 8

    def test_context_var_propagation(self):
        """Test that context vars are set correctly."""
        ctx = TraceContext.start("RELIANCE-EQ")

        assert ctx.get_trace_id() == ctx.trace_id
        assert ctx.get_tick_id() == ctx.tick_id

    def test_different_symbols_different_contexts(self):
        ctx1 = TraceContext.start("RELIANCE-EQ")
        ctx2 = TraceContext.start("TCS-EQ")

        assert ctx1.symbol != ctx2.symbol
        assert ctx1.trace_id != ctx2.trace_id
