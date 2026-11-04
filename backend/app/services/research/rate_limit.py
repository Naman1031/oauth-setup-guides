"""In-process rate limiting for the research endpoint (no Redis, per the spec).

LIMITATION: counters live in this server process's memory. They reset on
restart and are not shared between multiple instances, which is fine for a
single small Render instance.

Three independent limits protect the API budget:
- per client IP per hour,
- for the whole server per UTC day,
- concurrent research runs.
"""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class LimitDecision:
    allowed: bool
    reason: str = ""  # "ip_hourly" | "daily" | "busy"
    retry_after_seconds: int = 0


class ResearchRateLimiter:
    def __init__(self, per_ip_per_hour: int, per_day: int, max_concurrent: int, clock=time.monotonic) -> None:
        self.per_ip_per_hour = per_ip_per_hour
        self.per_day = per_day
        self.max_concurrent = max_concurrent
        self._clock = clock
        self._lock = threading.Lock()  # requests run on several threads at once
        self._ip_hits: dict[str, deque[float]] = defaultdict(deque)
        self._day = ""
        self._day_count = 0
        self._running = 0

    def try_acquire(self, client_ip: str) -> LimitDecision:
        """Check every limit and, if all pass, reserve a slot. Call release() when done."""
        now = self._clock()
        today = datetime.now(UTC).date().isoformat()
        with self._lock:
            if today != self._day:
                self._day, self._day_count = today, 0

            hits = self._ip_hits[client_ip]
            while hits and now - hits[0] >= 3600:  # sliding one-hour window
                hits.popleft()

            if self._running >= self.max_concurrent:
                return LimitDecision(False, "busy", 30)
            if len(hits) >= self.per_ip_per_hour:
                return LimitDecision(False, "ip_hourly", int(3600 - (now - hits[0])) + 1)
            if self._day_count >= self.per_day:
                return LimitDecision(False, "daily", 3600)

            hits.append(now)
            self._day_count += 1
            self._running += 1
            return LimitDecision(True)

    def release(self) -> None:
        with self._lock:
            self._running = max(0, self._running - 1)
