"""Detect cron jobs that have been running longer than their configured timeout."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cronwatcher.config import JobConfig


@dataclass
class TimeoutViolation:
    job_name: str
    started_at: datetime
    timeout_seconds: int
    elapsed_seconds: float

    def __str__(self) -> str:
        return (
            f"Job '{self.job_name}' exceeded timeout of {self.timeout_seconds}s "
            f"(running for {self.elapsed_seconds:.1f}s since {self.started_at.isoformat()})"
        )


@dataclass
class JobTimeoutTracker:
    """Tracks when jobs started so timeouts can be detected."""

    _start_times: Dict[str, datetime] = field(default_factory=dict)

    def record_start(self, job_name: str, started_at: Optional[datetime] = None) -> None:
        """Record that a job has started executing."""
        self._start_times[job_name] = started_at or datetime.utcnow()

    def record_finish(self, job_name: str) -> None:
        """Remove the start record once a job finishes successfully."""
        self._start_times.pop(job_name, None)

    def started_at(self, job_name: str) -> Optional[datetime]:
        return self._start_times.get(job_name)

    def check_timeouts(
        self,
        job_configs: List[JobConfig],
        now: Optional[datetime] = None,
    ) -> List[TimeoutViolation]:
        """Return violations for any in-flight jobs that have exceeded their timeout."""
        now = now or datetime.utcnow()
        violations: List[TimeoutViolation] = []

        timeout_map = {
            cfg.name: cfg.timeout_seconds
            for cfg in job_configs
            if getattr(cfg, "timeout_seconds", None) is not None
        }

        for job_name, started_at in list(self._start_times.items()):
            timeout_seconds = timeout_map.get(job_name)
            if timeout_seconds is None:
                continue
            elapsed = (now - started_at).total_seconds()
            if elapsed > timeout_seconds:
                violations.append(
                    TimeoutViolation(
                        job_name=job_name,
                        started_at=started_at,
                        timeout_seconds=timeout_seconds,
                        elapsed_seconds=elapsed,
                    )
                )
        return violations
