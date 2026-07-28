"""Metrics must be bounded in memory and thread-safe."""
import threading

from scalpr.observability.metrics import HistogramMetric, MetricsRegistry


def test_histogram_should_bound_values():
    """Histogram must not grow unbounded — use deque with maxlen."""
    hist = HistogramMetric(name="test", description="test")
    for i in range(20000):
        hist.observe(float(i))
    assert hist.count() <= 10000, f"Histogram grew to {hist.count()} — unbounded memory leak"


def test_counter_increment_should_be_thread_safe():
    """Concurrent counter increments must not lose counts."""
    registry = MetricsRegistry()
    counter = registry.register_counter("concurrent_test")
    errors = []

    def increment():
        try:
            for _ in range(1000):
                counter.increment()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=increment) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert counter.value == 10000, f"Expected 10000, got {counter.value}"
