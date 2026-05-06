"""Generates periodic status reports summarizing job health."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.history import HistoryLog, HistoryEntry
from cronwatcher.scheduler import Scheduler


@dataclass
class JobReport:
    job_name: str
    total_runs: int
    failed_runs: int
    missed_runs: int
    last_seen: Optional[datetime]
    success_rate: float


@dataclass
class StatusReport:
    generated_at: datetime
    jobs: List[JobReport] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return all(j.failed_runs == 0 and j.missed_runs == 0 for j in self.jobs)


class Reporter:
    def __init__(self, scheduler: Scheduler, history: HistoryLog) -> None:
        self._scheduler = scheduler
        self._history = history

    def generate(self) -> StatusReport:
        report = StatusReport(generated_at=datetime.now(timezone.utc))
        for job_name in self._scheduler.job_names():
            entries: List[HistoryEntry] = self._history.entries_for(job_name)
            total = len(entries)
            failed = sum(1 for e in entries if e.status == "failure")
            missed = sum(1 for e in entries if e.status == "missed")
            last_seen = max((e.timestamp for e in entries), default=None)
            rate = round((total - failed - missed) / total * 100, 1) if total else 0.0
            report.jobs.append(
                JobReport(
                    job_name=job_name,
                    total_runs=total,
                    failed_runs=failed,
                    missed_runs=missed,
                    last_seen=last_seen,
                    success_rate=rate,
                )
            )
        return report

    def format_text(self, report: StatusReport) -> str:
        lines = [
            f"CronWatcher Status Report — {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Overall healthy: {report.healthy}",
            "-" * 50,
        ]
        for job in report.jobs:
            last = job.last_seen.strftime("%Y-%m-%d %H:%M UTC") if job.last_seen else "never"
            lines.append(
                f"[{job.job_name}] runs={job.total_runs} failed={job.failed_runs} "
                f"missed={job.missed_runs} success={job.success_rate}% last_seen={last}"
            )
        return "\n".join(lines)
