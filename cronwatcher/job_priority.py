"""Job priority levels and priority-aware alert filtering."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Optional


class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_str(cls, value: str) -> "Priority":
        normalised = value.strip().upper()
        try:
            return cls[normalised]
        except KeyError:
            valid = ", ".join(m.lower() for m in cls.__members__)
            raise ValueError(f"Unknown priority {value!r}. Valid values: {valid}")

    def __str__(self) -> str:  # pragma: no cover
        return self.name.lower()


@dataclass
class JobPriorityMap:
    """Stores per-job priority assignments and exposes lookup helpers."""

    _priorities: Dict[str, Priority] = field(default_factory=dict)

    def set(self, job_id: str, priority: Priority) -> None:
        if not job_id:
            raise ValueError("job_id must be a non-empty string")
        self._priorities[job_id] = priority

    def get(self, job_id: str, default: Priority = Priority.MEDIUM) -> Priority:
        return self._priorities.get(job_id, default)

    def remove(self, job_id: str) -> None:
        self._priorities.pop(job_id, None)

    def all(self) -> Dict[str, Priority]:
        return dict(self._priorities)

    def to_dict(self) -> Dict[str, str]:
        return {jid: p.name.lower() for jid, p in self._priorities.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "JobPriorityMap":
        obj = cls()
        for job_id, raw in data.items():
            obj.set(job_id, Priority.from_str(raw))
        return obj


def minimum_priority_filter(
    job_id: str,
    priority_map: JobPriorityMap,
    minimum: Priority,
) -> bool:
    """Return True if the job's priority meets or exceeds *minimum*."""
    return priority_map.get(job_id) >= minimum
