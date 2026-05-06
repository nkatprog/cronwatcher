"""Heartbeat receiver for cron jobs.

Cron jobs ping this module via a simple HTTP endpoint or CLI call
to signal successful execution. The HeartbeatReceiver records the
timestamp and delegates to the Scheduler.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatRecord:
    job_name: str
    received_at: float = field(default_factory=time.time)
    metadata: Dict[str, str] = field(default_factory=dict)


class HeartbeatReceiver:
    """Receives and records heartbeat pings from monitored cron jobs."""

    def __init__(self, scheduler) -> None:
        self._scheduler = scheduler
        self._history: Dict[str, list] = {}

    def ping(self, job_name: str, metadata: Optional[Dict[str, str]] = None) -> HeartbeatRecord:
        """Record a heartbeat for the given job.

        Args:
            job_name: Name of the cron job as defined in config.
            metadata: Optional key/value pairs (e.g. exit_code, host).

        Returns:
            The created HeartbeatRecord.

        Raises:
            ValueError: If job_name is not registered in the scheduler.
        """
        if job_name not in self._scheduler.jobs:
            raise ValueError(f"Unknown job: '{job_name}'. Register it in the config first.")

        record = HeartbeatRecord(job_name=job_name, metadata=metadata or {})
        self._scheduler.record_heartbeat(job_name, record.received_at)

        self._history.setdefault(job_name, []).append(record)
        logger.info("Heartbeat received for job '%s' at %.3f", job_name, record.received_at)
        return record

    def last_ping(self, job_name: str) -> Optional[HeartbeatRecord]:
        """Return the most recent heartbeat record for a job, or None."""
        records = self._history.get(job_name)
        return records[-1] if records else None

    def history(self, job_name: str) -> list:
        """Return full heartbeat history for a job."""
        return list(self._history.get(job_name, []))
