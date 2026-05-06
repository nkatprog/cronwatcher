"""Silence windows: suppress alerts during scheduled maintenance periods."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional


@dataclass
class SilenceWindow:
    """Defines a recurring daily silence window for a job (or all jobs)."""

    start: time  # e.g. 02:00
    end: time    # e.g. 04:00
    job_name: Optional[str] = None  # None means applies to all jobs

    def is_active(self, at: Optional[datetime] = None) -> bool:
        """Return True if *at* (default: now) falls within this window."""
        now = (at or datetime.now()).time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= now < self.end
        # Overnight window, e.g. 23:00 – 01:00
        return now >= self.start or now < self.end

    def to_dict(self) -> dict:
        return {
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
            "job_name": self.job_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SilenceWindow":
        return cls(
            start=time.fromisoformat(data["start"]),
            end=time.fromisoformat(data["end"]),
            job_name=data.get("job_name"),
        )


@dataclass
class SilenceManager:
    """Manages a collection of silence windows and persists them to disk."""

    path: str
    windows: List[SilenceWindow] = field(default_factory=list)

    def __post_init__(self) -> None:
        if os.path.exists(self.path):
            self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, window: SilenceWindow) -> None:
        self.windows.append(window)
        self._save()

    def remove(self, index: int) -> None:
        self.windows.pop(index)
        self._save()

    def is_silenced(self, job_name: str, at: Optional[datetime] = None) -> bool:
        """Return True if *job_name* is currently silenced."""
        return any(
            w.is_active(at)
            for w in self.windows
            if w.job_name is None or w.job_name == job_name
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        with open(self.path, "w") as fh:
            json.dump([w.to_dict() for w in self.windows], fh, indent=2)

    def _load(self) -> None:
        with open(self.path) as fh:
            self.windows = [SilenceWindow.from_dict(d) for d in json.load(fh)]
