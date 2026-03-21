import time
import threading
from collections import defaultdict, deque


class RateLimiterCore:
    """
    Supports two algorithms:
      - token_bucket  : smooth traffic, allows short bursts
      - sliding_window: strict rolling window per client
    The ML engine can call set_limit() to auto-tune these at runtime.
    """

    DEFAULT_LIMIT = 10       # requests per window
    DEFAULT_WINDOW = 10      # seconds
    DEFAULT_ALGORITHM = "token_bucket"

    def __init__(self, telemetry=None):
        self.telemetry = telemetry
        self.lock = threading.Lock()

        self.limit = self.DEFAULT_LIMIT
        self.window = self.DEFAULT_WINDOW
        self.algorithm = self.DEFAULT_ALGORITHM

        # Token bucket state per client
        self._buckets = defaultdict(lambda: {
            "tokens": self.limit,
            "last_refill": time.time(),
        })

        # Sliding window state per client
        self._windows = defaultdict(deque)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def check(self, client_id: str) -> tuple[bool, dict]:
        with self.lock:
            if self.algorithm == "token_bucket":
                allowed = self._token_bucket_check(client_id)
            else:
                allowed = self._sliding_window_check(client_id)

            current_rate = self._current_rate(client_id)
            return allowed, {
                "algorithm": self.algorithm,
                "limit": self.limit,
                "window": self.window,
                "current_rate": current_rate,
            }

    def set_limit(self, new_limit: int, algorithm: str = None):
        with self.lock:
            self.limit = max(1, new_limit)
            if algorithm:
                self.algorithm = algorithm
            # Reset state so new limits take effect immediately
            self._buckets.clear()
            self._windows.clear()

    def get_config(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "limit": self.limit,
            "window": self.window,
        }

    def reset(self):
        with self.lock:
            self.limit = self.DEFAULT_LIMIT
            self.window = self.DEFAULT_WINDOW
            self.algorithm = self.DEFAULT_ALGORITHM
            self._buckets.clear()
            self._windows.clear()

    # ------------------------------------------------------------------ #
    #  Algorithms                                                          #
    # ------------------------------------------------------------------ #

    def _token_bucket_check(self, client_id: str) -> bool:
        bucket = self._buckets[client_id]
        now = time.time()
        elapsed = now - bucket["last_refill"]

        # Refill tokens proportionally to elapsed time
        refill = elapsed * (self.limit / self.window)
        bucket["tokens"] = min(self.limit, bucket["tokens"] + refill)
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False

    def _sliding_window_check(self, client_id: str) -> bool:
        now = time.time()
        window_start = now - self.window
        dq = self._windows[client_id]

        # Remove timestamps outside the window
        while dq and dq[0] < window_start:
            dq.popleft()

        if len(dq) < self.limit:
            dq.append(now)
            return True
        return False

    def _current_rate(self, client_id: str) -> float:
        """Returns requests/sec for a client over the last window."""
        if self.algorithm == "sliding_window":
            now = time.time()
            dq = self._windows[client_id]
            count = sum(1 for t in dq if t > now - self.window)
            return round(count / self.window, 3)
        else:
            bucket = self._buckets[client_id]
            used = self.limit - bucket["tokens"]
            return round(max(0, used) / self.window, 3)