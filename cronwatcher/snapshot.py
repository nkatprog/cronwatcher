"""Periodic state snapshots for cronwatcher job status."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class JobSnapshot:
    job_name: str
    last_heartbeat: Optional[datetime]
    missed: bool
    consecutive_misses: int

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "missed": self.missed,
            "consecutive_misses": self.consecutive_misses,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobSnapshot":
        lh = data.get("last_heartbeat")
        return cls(
            job_name=data["job_name"],
            last_heartbeat=datetime.fromisoformat(lh) if lh else None,
            missed=data["missed"],
            consecutive_misses=data["consecutive_misses"],
        )


@dataclass
class StateSnapshot:
    captured_at: datetime
    jobs: List[JobSnapshot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "captured_at": self.captured_at.isoformat(),
            "jobs": [j.to_dict() for j in self.jobs],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StateSnapshot":
        return cls(
            captured_at=datetime.fromisoformat(data["captured_at"]),
            jobs=[JobSnapshot.from_dict(j) for j in data.get("jobs", [])],
        )


class SnapshotManager:
    """Writes and reads state snapshots to/from a JSON file."""

    def __init__(self, snapshot_path: str) -> None:
        self._path = snapshot_path

    def save(self, snapshot: StateSnapshot) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(snapshot.to_dict(), fh, indent=2)
        os.replace(tmp, self._path)

    def load(self) -> Optional[StateSnapshot]:
        if not os.path.exists(self._path):
            return None
        with open(self._path) as fh:
            return StateSnapshot.from_dict(json.load(fh))

    def capture(self, scheduler) -> StateSnapshot:
        """Build a snapshot from a Scheduler instance."""
        now = datetime.now(timezone.utc)
        jobs: List[JobSnapshot] = []
        for name, state in scheduler.states.items():
            jobs.append(
                JobSnapshot(
                    job_name=name,
                    last_heartbeat=state.last_heartbeat,
                    missed=state.check_missed(now),
                    consecutive_misses=state.consecutive_misses,
                )
            )
        snap = StateSnapshot(captured_at=now, jobs=jobs)
        self.save(snap)
        return snap
