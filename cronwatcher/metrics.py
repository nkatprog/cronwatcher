"""Collects and exposes runtime metrics for monitored cron jobs."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class JobMetrics:
    job_name: str
    total_pings: int = 0
    total_missed: int = 0
    total_alerts_sent: int = 0
    last_ping_at: Optional[datetime] = None
    last_missed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "total_pings": self.total_pings,
            "total_missed": self.total_missed,
            "total_alerts_sent": self.total_alerts_sent,
            "last_ping_at": self.last_ping_at.isoformat() if self.last_ping_at else None,
            "last_missed_at": self.last_missed_at.isoformat() if self.last_missed_at else None,
        }


class MetricsCollector:
    def __init__(self) -> None:
        self._metrics: Dict[str, JobMetrics] = {}

    def _get_or_create(self, job_name: str) -> JobMetrics:
        if job_name not in self._metrics:
            self._metrics[job_name] = JobMetrics(job_name=job_name)
        return self._metrics[job_name]

    def record_ping(self, job_name: str, at: Optional[datetime] = None) -> None:
        m = self._get_or_create(job_name)
        m.total_pings += 1
        m.last_ping_at = at or datetime.utcnow()

    def record_missed(self, job_name: str, at: Optional[datetime] = None) -> None:
        m = self._get_or_create(job_name)
        m.total_missed += 1
        m.last_missed_at = at or datetime.utcnow()

    def record_alert(self, job_name: str) -> None:
        self._get_or_create(job_name).total_alerts_sent += 1

    def get(self, job_name: str) -> Optional[JobMetrics]:
        return self._metrics.get(job_name)

    def all(self) -> Dict[str, JobMetrics]:
        return dict(self._metrics)

    def summary(self) -> list:
        return [m.to_dict() for m in self._metrics.values()]
