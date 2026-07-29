"""Thread-safe metrics registry for SCALPR trading platform."""

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class CounterMetric:
    """Monotonically increasing counter metric."""
    name: str
    value: int = 0
    description: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, init=False)

    def increment(self, amount: int = 1) -> None:
        with self._lock:
            self.value += amount


@dataclass
class HistogramMetric:
    """Histogram metric for tracking latency distributions."""
    name: str
    values: deque[float] = field(default_factory=lambda: deque(maxlen=10000))
    description: str = ""

    def observe(self, value: float) -> None:
        self.values.append(value)

    def p50(self) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        return sorted_vals[len(sorted_vals) // 2]

    def p99(self) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        return sorted_vals[int(len(sorted_vals) * 0.99)]

    def count(self) -> int:
        return len(self.values)


@dataclass
class GaugeMetric:
    """Gauge metric for point-in-time values."""
    name: str
    value: float = 0.0
    description: str = ""

    def set(self, value: float) -> None:
        self.value = value


class MetricsRegistry:
    """Thread-safe metrics registry for production monitoring."""

    def __init__(self) -> None:
        self._counters: dict[str, CounterMetric] = {}
        self._histograms: dict[str, HistogramMetric] = {}
        self._gauges: dict[str, GaugeMetric] = {}
        self._lock = threading.Lock()

        # Initialize core metrics
        self._init_core_metrics()

    def _init_core_metrics(self) -> None:
        """Initialize standard trading platform metrics."""
        # Counters
        self.register_counter("orders_submitted", "Total orders submitted to broker")
        self.register_counter("orders_rejected", "Total orders rejected by risk checks")
        self.register_counter("orders_filled", "Total orders filled")
        self.register_counter("fills_received", "Total fill events received")
        self.register_counter("strategy_ticks", "Total ticks routed to strategies")
        self.register_counter("strategy_errors", "Total strategy execution errors")
        self.register_counter("strategy_timeouts", "Total strategy timeout events")
        self.register_counter("ws_reconnects", "WebSocket reconnect count")
        self.register_counter("token_refreshes", "Token refresh count")
        self.register_counter("rate_limit_exhausted", "Rate limit exhaustion events")
        self.register_counter("market_data_gaps", "Market data gap events")
        self.register_counter("pnl_divergences", "PnL divergence events")

        # Histograms
        self.register_histogram("order_routing_latency_ms", "Order routing latency")
        self.register_histogram("strategy_execution_latency_ms", "Strategy execution latency")
        self.register_histogram("tick_processing_latency_ms", "End-to-end tick processing latency")
        self.register_histogram("persistence_latency_ms", "Database persistence latency")
        self.register_histogram("order_latency_ms", "Order submission to fill latency")

        # Gauges
        self.register_gauge("active_positions", "Current open positions")
        self.register_gauge("circuit_breaker_state", "Circuit breaker state (0=closed, 1=open)")
        self.register_gauge("event_bus_subscribers", "Active event bus subscribers")

    def register_counter(self, name: str, description: str = "") -> CounterMetric:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = CounterMetric(name, 0, description)
            return self._counters[name]

    def register_histogram(self, name: str, description: str = "") -> HistogramMetric:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = HistogramMetric(name=name, description=description)
            return self._histograms[name]

    def register_gauge(self, name: str, description: str = "") -> GaugeMetric:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = GaugeMetric(name, 0.0, description)
            return self._gauges[name]

    def get_counter(self, name: str) -> CounterMetric | None:
        return self._counters.get(name)

    def get_histogram(self, name: str) -> HistogramMetric | None:
        return self._histograms.get(name)

    def get_gauge(self, name: str) -> GaugeMetric | None:
        return self._gauges.get(name)

    def snapshot(self) -> dict[str, Any]:
        """Return current metrics snapshot for /metrics endpoint."""
        with self._lock:
            return {
                "counters": {name: counter.value for name, counter in self._counters.items()},
                "histograms": {
                    name: {"p50": hist.p50(), "p99": hist.p99(), "count": hist.count()}
                    for name, hist in self._histograms.items()
                },
                "gauges": {name: gauge.value for name, gauge in self._gauges.items()},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Global metrics instance
metrics = MetricsRegistry()
