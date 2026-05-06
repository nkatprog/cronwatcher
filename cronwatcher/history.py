"""Persistent history log for cron job events."""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class HistoryEntry:
    job_name: str
    event_type: str  # 'heartbeat', 'missed', 'failure'
    timestamp: str
    message: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(
            job_name=data["job_name"],
            event_type=data["event_type"],
            timestamp=data["timestamp"],
            message=data.get("message"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


class HistoryLog:
    def __init__(self, path: str, max_entries: int = 1000):
        self._path = path
        self._max_entries = max_entries
        self._entries: List[HistoryEntry] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r") as f:
                raw = json.load(f)
            self._entries = [HistoryEntry.from_dict(r) for r in raw]
        except (json.JSONDecodeError, KeyError):
            self._entries = []

    def _save(self) -> None:
        with open(self._path, "w") as f:
            json.dump([e.to_dict() for e in self._entries], f, indent=2)

    def record(self, job_name: str, event_type: str, message: Optional[str] = None) -> HistoryEntry:
        entry = HistoryEntry(
            job_name=job_name,
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            message=message,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]
        self._save()
        return entry

    def get_all(self) -> List[HistoryEntry]:
        return list(self._entries)

    def get_for_job(self, job_name: str) -> List[HistoryEntry]:
        return [e for e in self._entries if e.job_name == job_name]

    def get_recent(self, limit: int = 50) -> List[HistoryEntry]:
        return self._entries[-limit:]
