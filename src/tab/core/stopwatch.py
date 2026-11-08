from collections.abc import Callable


class Stopwatch:
    """Accumulates running time across start/pause cycles using a monotonic clock."""

    def __init__(self, monotonic_clock_seconds: Callable[[], float]) -> None:
        self._monotonic_clock_seconds = monotonic_clock_seconds
        self._elapsed_seconds_before_last_start = 0.0
        self._clock_seconds_at_last_start: float | None = None

    @property
    def is_running(self) -> bool:
        return self._clock_seconds_at_last_start is not None

    def elapsed_seconds(self) -> float:
        if self._clock_seconds_at_last_start is None:
            return self._elapsed_seconds_before_last_start
        seconds_since_last_start = (
            self._monotonic_clock_seconds() - self._clock_seconds_at_last_start
        )
        return self._elapsed_seconds_before_last_start + seconds_since_last_start

    def start(self) -> None:
        if not self.is_running:
            self._clock_seconds_at_last_start = self._monotonic_clock_seconds()

    def pause(self) -> None:
        if self.is_running:
            self._elapsed_seconds_before_last_start = self.elapsed_seconds()
            self._clock_seconds_at_last_start = None

    def reset(self, elapsed_seconds: float = 0.0) -> None:
        """Stop and set the accumulated time (0 by default)."""
        self._elapsed_seconds_before_last_start = elapsed_seconds
        self._clock_seconds_at_last_start = None
