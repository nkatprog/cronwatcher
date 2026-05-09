"""Rate limiting for alert notifications to prevent alert storms."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RateLimitEntry:
    count: int = 0
    window_start: float = field(default_factory=time.time)
    last_sent: Optional[float] = None

    def reset(self, now: float) -> None:
        self.count = 0
        self.window_start = now


class RateLimiter:
    """Limits how many alerts can be sent per job within a rolling time window.

    Args:
        max_alerts: Maximum number of alerts allowed per window.
        window_seconds: Duration of the rolling window in seconds.
    """

    def __init__(self, max_alerts: int = 5, window_seconds: float = 3600.0) -> None:
        if max_alerts < 1:
            raise ValueError("max_alerts must be at least 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._max_alerts = max_alerts
        self._window_seconds = window_seconds
        self._entries: Dict[str, RateLimitEntry] = {}

    def _get_or_create(self, job_name: str, now: float) -> RateLimitEntry:
        entry = self._entries.get(job_name)
        if entry is None:
            entry = RateLimitEntry(window_start=now)
            self._entries[job_name] = entry
        return entry

    def is_allowed(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if an alert for *job_name* is allowed right now."""
        now = now if now is not None else time.time()
        entry = self._get_or_create(job_name, now)
        if now - entry.window_start >= self._window_seconds:
            entry.reset(now)
        return entry.count < self._max_alerts

    def record(self, job_name: str, now: Optional[float] = None) -> None:
        """Record that an alert was sent for *job_name*."""
        now = now if now is not None else time.time()
        entry = self._get_or_create(job_name, now)
        if now - entry.window_start >= self._window_seconds:
            entry.reset(now)
        entry.count += 1
        entry.last_sent = now

    def remaining(self, job_name: str, now: Optional[float] = None) -> int:
        """Return how many more alerts are allowed in the current window."""
        now = now if now is not None else time.time()
        entry = self._get_or_create(job_name, now)
        if now - entry.window_start >= self._window_seconds:
            entry.reset(now)
        return max(0, self._max_alerts - entry.count)

    def reset_job(self, job_name: str) -> None:
        """Manually clear rate-limit state for a specific job."""
        self._entries.pop(job_name, None)
