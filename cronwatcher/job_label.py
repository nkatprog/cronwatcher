"""Job label management: attach arbitrary key-value metadata to jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class JobLabels:
    """Key-value label set attached to a single job."""

    job_name: str
    labels: Dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> Optional[str]:
        """Return the value for *key*, or None if absent."""
        return self.labels.get(key)

    def set(self, key: str, value: str) -> None:
        """Add or overwrite a label."""
        if not key:
            raise ValueError("Label key must not be empty")
        self.labels[key] = value

    def remove(self, key: str) -> None:
        """Remove *key*; silently ignored if the key does not exist."""
        self.labels.pop(key, None)

    def to_dict(self) -> Dict[str, object]:
        return {"job_name": self.job_name, "labels": dict(self.labels)}

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "JobLabels":
        return cls(
            job_name=str(data["job_name"]),
            labels=dict(data.get("labels", {})),  # type: ignore[arg-type]
        )


class LabelRegistry:
    """Central store for labels across all monitored jobs."""

    def __init__(self) -> None:
        self._store: Dict[str, JobLabels] = {}

    def _get_or_create(self, job_name: str) -> JobLabels:
        if job_name not in self._store:
            self._store[job_name] = JobLabels(job_name=job_name)
        return self._store[job_name]

    def set_label(self, job_name: str, key: str, value: str) -> None:
        self._get_or_create(job_name).set(key, value)

    def get_label(self, job_name: str, key: str) -> Optional[str]:
        entry = self._store.get(job_name)
        return entry.get(key) if entry else None

    def remove_label(self, job_name: str, key: str) -> None:
        entry = self._store.get(job_name)
        if entry:
            entry.remove(key)

    def labels_for(self, job_name: str) -> Dict[str, str]:
        entry = self._store.get(job_name)
        return dict(entry.labels) if entry else {}

    def find_by_label(self, key: str, value: str) -> List[str]:
        """Return job names whose label *key* equals *value*."""
        return [
            name
            for name, jl in self._store.items()
            if jl.get(key) == value
        ]

    def all(self) -> List[JobLabels]:
        return list(self._store.values())
