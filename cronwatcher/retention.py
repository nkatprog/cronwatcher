"""Retention policy for pruning old history entries."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from cronwatcher.history import HistoryLog

logger = logging.getLogger(__name__)


class RetentionPolicy:
    """Defines how long history entries should be kept."""

    def __init__(self, max_age_days: int = 30, max_entries_per_job: Optional[int] = 100):
        if max_age_days <= 0:
            raise ValueError("max_age_days must be positive")
        if max_entries_per_job is not None and max_entries_per_job <= 0:
            raise ValueError("max_entries_per_job must be positive or None")
        self.max_age_days = max_age_days
        self.max_entries_per_job = max_entries_per_job

    def cutoff_time(self) -> datetime:
        return datetime.now(tz=timezone.utc) - timedelta(days=self.max_age_days)


class HistoryPruner:
    """Prunes history entries according to a retention policy."""

    def __init__(self, history: HistoryLog, policy: RetentionPolicy):
        self._history = history
        self._policy = policy

    def _prune_job(self, job_name: str, cutoff: datetime) -> int:
        """Prune entries for a single job. Returns the number of entries removed."""
        entries = self._history._entries[job_name]
        before = len(entries)
        entries[:] = [e for e in entries if e.timestamp >= cutoff]
        if self._policy.max_entries_per_job is not None:
            entries[:] = entries[-self._policy.max_entries_per_job:]
        return before - len(entries)

    def prune(self) -> int:
        """Remove stale entries. Returns the number of entries removed."""
        cutoff = self._policy.cutoff_time()
        removed = 0

        for job_name in list(self._history._entries.keys()):
            removed += self._prune_job(job_name, cutoff)

        if removed:
            self._history.save()
            logger.info("Pruned %d history entries.", removed)
        return removed
