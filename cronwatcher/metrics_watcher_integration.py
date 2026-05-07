"""Integrates MetricsCollector with Watcher events via thin hooks."""

from datetime import datetime
from typing import Optional

from cronwatcher.metrics import MetricsCollector


class MetricsHooks:
    """Callable hooks passed into Watcher or called from alerter/heartbeat code."""

    def __init__(self, collector: MetricsCollector) -> None:
        self._collector = collector

    def on_ping(self, job_name: str, at: Optional[datetime] = None) -> None:
        self._collector.record_ping(job_name, at=at)

    def on_missed(self, job_name: str, at: Optional[datetime] = None) -> None:
        self._collector.record_missed(job_name, at=at)

    def on_alert(self, job_name: str) -> None:
        self._collector.record_alert(job_name)
