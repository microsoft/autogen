import time
from typing import Protocol


class RateLimiter(Protocol):
    def sleep(self, *args, **kwargs): ...


class TimeRateLimiter:
    """A class to implement a time-based rate limiter.

    This rate limiter ensures that a certain operation does not exceed a specified frequency.
    It can be used to limit the rate of requests sent to a server or the rate of any repeated action.
    """

    def __init__(self, rate: float):
        """
        Args:
            rate (int): The frequency of the time-based rate limiter (NOT time interval).
        """
        self._time_interval_seconds = 1.0 / rate
        self._last_time_called = 0.0

    def sleep(self, *args, **kwargs):
        """Synchronously waits until enough time has passed to allow the next operation.

        If the elapsed time since the last operation is less than the required time interval,
        this method will block the execution by sleeping for the remaining time.
        """
        if self._elapsed_time() < self._time_interval_seconds:
            time.sleep(self._time_interval_seconds - self._elapsed_time())

        self._last_time_called = time.perf_counter()

    def _elapsed_time(self):
        return time.perf_counter() - self._last_time_called
