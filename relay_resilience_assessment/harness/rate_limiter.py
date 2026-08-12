"""A minimal token-bucket limiter used to hold every scenario to the
execution constraint of <= N requests/second (default 10)."""
import threading
import time


class RateLimiter:
    def __init__(self, rate_per_second: float):
        self.min_interval = 1.0 / rate_per_second if rate_per_second > 0 else 0
        self._lock = threading.Lock()
        self._next_allowed = time.monotonic()

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            wait = self._next_allowed - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._next_allowed = max(now, self._next_allowed) + self.min_interval
