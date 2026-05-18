"""Correlates related job failures to suppress redundant alerts."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


@dataclass
class CorrelationGroup:
    """A named group of job IDs that are considered correlated."""

    name: str
    job_ids: List[str]
    suppress_after: int = 1  # suppress alerts after this many failures in group

    @classmethod
    def from_dict(cls, data: dict) -> "CorrelationGroup":
        if not data.get("name"):
            raise ValueError("CorrelationGroup requires a non-empty name")
        if not data.get("job_ids"):
            raise ValueError("CorrelationGroup requires at least one job_id")
        suppress = data.get("suppress_after", 1)
        if suppress < 1:
            raise ValueError("suppress_after must be >= 1")
        return cls(
            name=data["name"],
            job_ids=list(data["job_ids"]),
            suppress_after=suppress,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "job_ids": list(self.job_ids),
            "suppress_after": self.suppress_after,
        }


@dataclass
class CorrelationState:
    """Tracks failure timestamps for jobs within a correlation group."""

    _failures: Dict[str, datetime] = field(default_factory=dict)

    def record_failure(self, job_id: str, ts: Optional[datetime] = None) -> None:
        self._failures[job_id] = ts or datetime.utcnow()

    def clear_failure(self, job_id: str) -> None:
        self._failures.pop(job_id, None)

    def active_failure_count(self, window_seconds: int = 300) -> int:
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        return sum(1 for ts in self._failures.values() if ts >= cutoff)


class JobCorrelationManager:
    """Determines whether an alert should be suppressed due to correlated failures."""

    def __init__(self, groups: List[CorrelationGroup], window_seconds: int = 300) -> None:
        self._groups = {g.name: g for g in groups}
        self._states: Dict[str, CorrelationState] = {
            g.name: CorrelationState() for g in groups
        }
        self._window = window_seconds

    def record_failure(self, job_id: str, ts: Optional[datetime] = None) -> None:
        for name, group in self._groups.items():
            if job_id in group.job_ids:
                self._states[name].record_failure(job_id, ts)

    def record_recovery(self, job_id: str) -> None:
        for name, group in self._groups.items():
            if job_id in group.job_ids:
                self._states[name].clear_failure(job_id)

    def is_suppressed(self, job_id: str) -> bool:
        """Return True if this job's alert should be suppressed due to group activity."""
        for name, group in self._groups.items():
            if job_id in group.job_ids:
                count = self._states[name].active_failure_count(self._window)
                if count > group.suppress_after:
                    return True
        return False
