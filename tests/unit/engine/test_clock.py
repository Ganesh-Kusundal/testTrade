from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from scalpr.engine.clock import Clock, LiveClock, StaticClock


class TestLiveClock:
    def test_timestamp_returns_datetime(self):
        clock = LiveClock()
        result = clock.timestamp()
        assert isinstance(result, datetime)

    def test_utc_now_returns_datetime(self):
        clock = LiveClock()
        result = clock.utc_now()
        assert isinstance(result, datetime)

    def test_timestamp_is_reasonable(self):
        clock = LiveClock()
        now = clock.timestamp()
        ref = datetime.now()
        assert abs((now - ref).total_seconds()) < 5

    def test_utc_now_is_close_to_utc(self):
        clock = LiveClock()
        u = clock.utc_now()
        ref = datetime.now(timezone.utc)
        assert abs((u - ref).total_seconds()) < 5

    def test_timestamp_and_utc_now_differ_by_tz_offset(self):
        clock = LiveClock()
        ts = clock.timestamp()
        utc = clock.utc_now()
        # timestamp() is local (naive), utc_now() is aware UTC
        # They should differ by roughly the local tz offset
        assert ts.tzinfo is None
        assert utc.tzinfo is not None

    def test_consecutive_calls_different(self):
        clock = LiveClock()
        t1 = clock.timestamp()
        t2 = clock.timestamp()
        assert t2 >= t1

    def test_isinstance_clock(self):
        assert isinstance(LiveClock(), Clock)


class TestStaticClockDefaults:
    def test_default_start_is_2024_01_01(self):
        clock = StaticClock()
        assert clock.timestamp() == datetime(2024, 1, 1)

    def test_utc_now_default_start(self):
        clock = StaticClock()
        assert clock.utc_now() == datetime(2024, 1, 1)

    def test_timestamp_and_utc_now_identical(self):
        clock = StaticClock()
        assert clock.timestamp() == clock.utc_now()

    def test_isinstance_clock(self):
        assert isinstance(StaticClock(), Clock)


class TestStaticClockAdvance:
    def test_advance_one_second(self):
        clock = StaticClock()
        clock.advance(1)
        assert clock.timestamp() == datetime(2024, 1, 1, 0, 0, 1)

    def test_advance_sixty_seconds(self):
        clock = StaticClock()
        clock.advance(60)
        assert clock.timestamp() == datetime(2024, 1, 1, 0, 1, 0)

    def test_advance_one_hour(self):
        clock = StaticClock()
        clock.advance(3600)
        assert clock.timestamp() == datetime(2024, 1, 1, 1, 0, 0)

    def test_advance_zero_does_nothing(self):
        clock = StaticClock()
        clock.advance(0)
        assert clock.timestamp() == datetime(2024, 1, 1)

    def test_advance_fractional_seconds(self):
        clock = StaticClock()
        clock.advance(1.5)
        ts = clock.timestamp()
        datetime(2024, 1, 1, 0, 0, 0, 500000)
        assert ts == datetime(2024, 1, 1, 0, 0, 1, 500000)

    def test_advance_negative_goes_backward(self):
        clock = StaticClock(start_time=datetime(2024, 6, 15))
        clock.advance(-3600)
        assert clock.timestamp() == datetime(2024, 6, 15) - timedelta(hours=1)

    def test_multiple_advances_accumulate(self):
        clock = StaticClock()
        clock.advance(10)
        clock.advance(20)
        clock.advance(30)
        assert clock.timestamp() == datetime(2024, 1, 1, 0, 1, 0)

    def test_advance_large_value(self):
        clock = StaticClock()
        clock.advance(86400 * 366)
        assert clock.timestamp() == datetime(2025, 1, 1)


class TestStaticClockSetTime:
    def test_set_time_explicit(self):
        clock = StaticClock()
        dt = datetime(2025, 12, 25, 10, 30, 0)
        clock.set_time(dt)
        assert clock.timestamp() == dt

    def test_set_time_to_earlier(self):
        clock = StaticClock(start_time=datetime(2024, 6, 15))
        clock.set_time(datetime(2024, 1, 1))
        assert clock.timestamp() == datetime(2024, 1, 1)

    def test_set_time_then_advance(self):
        clock = StaticClock()
        clock.set_time(datetime(2024, 6, 1))
        clock.advance(3600)
        assert clock.timestamp() == datetime(2024, 6, 1, 1, 0, 0)

    def test_advance_then_set_time(self):
        clock = StaticClock()
        clock.advance(3600)
        clock.set_time(datetime(2020, 1, 1))
        assert clock.timestamp() == datetime(2020, 1, 1)


class TestCustomStartTime:
    def test_custom_start_time(self):
        dt = datetime(2023, 12, 31, 23, 59, 59)
        clock = StaticClock(start_time=dt)
        assert clock.timestamp() == dt

    def test_custom_start_utc_now(self):
        dt = datetime(2023, 6, 15, 12, 0, 0)
        clock = StaticClock(start_time=dt)
        assert clock.utc_now() == dt

    def test_custom_start_then_advance(self):
        dt = datetime(2023, 1, 1)
        clock = StaticClock(start_time=dt)
        clock.advance(86400)
        assert clock.timestamp() == datetime(2023, 1, 2)


class TestMultipleInstances:
    def test_independent_clocks(self):
        c1 = StaticClock(start_time=datetime(2024, 1, 1))
        c2 = StaticClock(start_time=datetime(2024, 6, 1))
        assert c1.timestamp() != c2.timestamp()
        c1.advance(86400)
        assert c1.timestamp() == datetime(2024, 1, 2)
        assert c2.timestamp() == datetime(2024, 6, 1)

    def test_three_independent_clocks(self):
        c1 = StaticClock()
        c2 = StaticClock()
        c3 = StaticClock()
        c1.advance(1)
        c2.advance(2)
        c3.advance(3)
        assert c1.timestamp() == datetime(2024, 1, 1, 0, 0, 1)
        assert c2.timestamp() == datetime(2024, 1, 1, 0, 0, 2)
        assert c3.timestamp() == datetime(2024, 1, 1, 0, 0, 3)


class TestClockABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            Clock()

    def test_liveclock_concrete(self):
        LiveClock()

    def test_staticclock_concrete(self):
        StaticClock()


class TestEdgeCases:
    def test_utc_now_no_tzinfo(self):
        clock = StaticClock()
        assert clock.utc_now().tzinfo is None

    def test_liveclock_utc_now_has_tzinfo(self):
        clock = LiveClock()
        assert clock.utc_now().tzinfo is not None

    def test_staticclock_returns_same_time_before_advance(self):
        clock = StaticClock()
        t1 = clock.timestamp()
        t2 = clock.timestamp()
        assert t1 == t2

    def test_staticclock_advance_microseconds(self):
        clock = StaticClock()
        clock.advance(0.000001)
        assert clock.timestamp() == datetime(2024, 1, 1, 0, 0, 0, 1)
