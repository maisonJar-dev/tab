from tab.core.stopwatch import Stopwatch


class FakeMonotonicClock:
    def __init__(self) -> None:
        self.current_seconds = 0.0

    def __call__(self) -> float:
        return self.current_seconds


def test_accumulates_only_while_running() -> None:
    fake_clock = FakeMonotonicClock()
    stopwatch = Stopwatch(fake_clock)
    stopwatch.start()
    fake_clock.current_seconds += 3
    stopwatch.pause()
    fake_clock.current_seconds += 10
    assert stopwatch.elapsed_seconds() == 3


def test_reset_to_a_time_then_start_keeps_counting_from_there() -> None:
    """How the splash skips to the end of its animation."""
    fake_clock = FakeMonotonicClock()
    stopwatch = Stopwatch(fake_clock)
    stopwatch.start()
    fake_clock.current_seconds += 1
    stopwatch.reset(elapsed_seconds=5)
    stopwatch.start()
    fake_clock.current_seconds += 2
    assert stopwatch.elapsed_seconds() == 7
