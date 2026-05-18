"""Job annotation support — attach arbitrary key/value notes to jobs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class JobAnnotations:
    """Stores free-form string annotations for a single job."""
    _data: Dict[str, str] = field(default_factory=dict)

    def set(self, key: str, value: str) -> None:
        if not key:
            raise ValueError("Annotation key must not be empty")
        self._data[key] = value

    def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    def remove(self, key: str) -> None:
        self._data.pop(key, None)

    def all(self) -> Dict[str, str]:
        return dict(self._data)

    def to_dict(self) -> Dict[str, str]:
        return dict(self._data)

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "JobAnnotations":
        obj = cls()
        for k, v in data.items():
            obj.set(k, v)
        return obj


class AnnotationStore:
    """Persists job annotations to a JSON file."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._store: Dict[str, JobAnnotations] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, job_id: str) -> JobAnnotations:
        if job_id not in self._store:
            self._store[job_id] = JobAnnotations()
        return self._store[job_id]

    def set(self, job_id: str, key: str, value: str) -> None:
        self.get(job_id).set(key, value)
        self._save()

    def remove(self, job_id: str, key: str) -> None:
        self.get(job_id).remove(key)
        self._save()

    def all_for_job(self, job_id: str) -> Dict[str, str]:
        return self.get(job_id).all()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path, "r", encoding="utf-8") as fh:
            raw: Dict[str, Dict[str, str]] = json.load(fh)
        for job_id, annotations in raw.items():
            self._store[job_id] = JobAnnotations.from_dict(annotations)

    def _save(self) -> None:
        payload = {job_id: ann.to_dict() for job_id, ann in self._store.items()}
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
