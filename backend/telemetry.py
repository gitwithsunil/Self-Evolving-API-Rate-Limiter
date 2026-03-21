import time
import threading
from collections import deque, defaultdict
from datetime import datetime


class TelemetryCollector:
    """
    Stores all request events in memory.
    Provides stats and recent logs for the dashboard and ML engine.
    """

    MAX_LOGS = 1000

    def __init__(self):
        self.lock = threading.Lock()
        self._logs = deque(maxlen=self.MAX_LOGS)
        self._total_requests = 0
        self._denied_requests = 0
        self._client_counts = defaultdict(int)
        self._recent_timestamps = deque(maxlen=200)   # for rate calc

    def record(self, client_id: str, allowed: bool, algorithm: str, limit: int, current_rate: float):
        now = time.time()
        with self.lock:
            self._total_requests += 1
            if not allowed:
                self._denied_requests += 1
            self._client_counts[client_id] += 1
            self._recent_timestamps.append(now)
            self._logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "unix_ts": now,
                "client_id": client_id,
                "allowed": allowed,
                "algorithm": algorithm,
                "limit": limit,
                "current_rate": current_rate,
            })

    def get_stats(self) -> dict:
        with self.lock:
            now = time.time()
            # Requests in last 10 seconds
            recent_count = sum(1 for t in self._recent_timestamps if t > now - 10)
            recent_rate = round(recent_count / 10.0, 3)

            return {
                "total_requests": self._total_requests,
                "denied_requests": self._denied_requests,
                "allowed_requests": self._total_requests - self._denied_requests,
                "deny_ratio": round(
                    self._denied_requests / self._total_requests, 4
                ) if self._total_requests > 0 else 0.0,
                "recent_rate": recent_rate,
                "unique_clients": len(self._client_counts),
                "top_clients": sorted(
                    self._client_counts.items(), key=lambda x: x[1], reverse=True
                )[:5],
            }

    def get_recent_logs(self, n: int = 100) -> list:
        with self.lock:
            logs = list(self._logs)
        return list(reversed(logs))[:n]

    def reset(self):
        with self.lock:
            self._logs.clear()
            self._total_requests = 0
            self._denied_requests = 0
            self._client_counts.clear()
            self._recent_timestamps.clear()