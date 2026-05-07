"""Audit log — records configuration changes and significant daemon events."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class AuditEntry:
    timestamp: datetime
    event_type: str          # e.g. "config_loaded", "silence_added", "job_missed"
    actor: str               # "daemon", "cli", or a username
    detail: str
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "actor": self.actor,
            "detail": self.detail,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=data["event_type"],
            actor=data["actor"],
            detail=data["detail"],
            extra=data.get("extra", {}),
        )


class AuditLog:
    def __init__(self, log_path: str) -> None:
        self._path = log_path
        self._entries: List[AuditEntry] = []
        self._load()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def record(self, event_type: str, detail: str,
               actor: str = "daemon", extra: Optional[dict] = None) -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.now(tz=timezone.utc),
            event_type=event_type,
            actor=actor,
            detail=detail,
            extra=extra or {},
        )
        self._entries.append(entry)
        self._save()
        return entry

    def all_entries(self) -> List[AuditEntry]:
        return list(self._entries)

    def entries_for(self, event_type: str) -> List[AuditEntry]:
        return [e for e in self._entries if e.event_type == event_type]

    # ------------------------------------------------------------------ #
    #  Persistence                                                         #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path) as fh:
            raw = json.load(fh)
        self._entries = [AuditEntry.from_dict(d) for d in raw]

    def _save(self) -> None:
        with open(self._path, "w") as fh:
            json.dump([e.to_dict() for e in self._entries], fh, indent=2)
