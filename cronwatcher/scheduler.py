import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from cronwatcher.config import JobConfig

logger = logging.getLogger(__name__)


class JobState:
    def __init__(self, job: JobConfig):
        self.job = job
        self.last_seen: Optional[datetime] = None
        self.missed_count: int = 0
        self.is_missed: bool = False

    def check_missed(self, now: Optional[datetime] = None) -> bool:
        """Return True if the job has missed its expected run window."""
        if now is None:
            now = datetime.utcnow()
        if self.last_seen is None:
            return False
        deadline = self.last_seen + timedelta(seconds=self.job.interval_seconds) + timedelta(seconds=self.job.grace_seconds)
        if now > deadline:
            if not self.is_missed:
                self.is_missed = True
                self.missed_count += 1
                logger.warning(
                    "Job '%s' missed its run. Expected by %s, now %s.",
                    self.job.name,
                    deadline.isoformat(),
                    now.isoformat(),
                )
            return True
        return False

    def record_heartbeat(self, now: Optional[datetime] = None) -> None:
        """Record a successful heartbeat/check-in for this job."""
        if now is None:
            now = datetime.utcnow()
        logger.info("Job '%s' heartbeat received at %s.", self.job.name, now.isoformat())
        self.last_seen = now
        self.is_missed = False


class Scheduler:
    def __init__(self, jobs: list[JobConfig]):
        self.states: Dict[str, JobState] = {
            job.name: JobState(job) for job in jobs
        }

    def heartbeat(self, job_name: str, now: Optional[datetime] = None) -> bool:
        """Register a heartbeat for a job. Returns False if job is unknown."""
        if job_name not in self.states:
            logger.error("Heartbeat received for unknown job '%s'.", job_name)
            return False
        self.states[job_name].record_heartbeat(now)
        return True

    def check_all(self, now: Optional[datetime] = None) -> list[str]:
        """Check all jobs for missed runs. Returns list of missed job names."""
        if now is None:
            now = datetime.utcnow()
        missed = []
        for name, state in self.states.items():
            if state.check_missed(now):
                missed.append(name)
        return missed

    def get_state(self, job_name: str) -> Optional[JobState]:
        return self.states.get(job_name)
