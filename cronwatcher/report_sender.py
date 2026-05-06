"""Sends generated status reports via the configured alert channel."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from cronwatcher.reporter import Reporter, StatusReport
from cronwatcher.alerter import Alerter, AlertEvent

logger = logging.getLogger(__name__)


class ReportSender:
    """Periodically sends a status report through the Alerter."""

    def __init__(
        self,
        reporter: Reporter,
        alerter: Alerter,
        interval_seconds: int = 3600,
    ) -> None:
        self._reporter = reporter
        self._alerter = alerter
        self._interval = timedelta(seconds=interval_seconds)
        self._last_sent: Optional[datetime] = None

    def due(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self._last_sent is None:
            return True
        return (now - self._last_sent) >= self._interval

    def send_if_due(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if not self.due(now):
            return False
        report = self._reporter.generate()
        self._dispatch(report)
        self._last_sent = now
        return True

    def _dispatch(self, report: StatusReport) -> None:
        body = self._reporter.format_text(report)
        event = AlertEvent(
            job_name="__report__",
            kind="report",
            message=body,
            timestamp=report.generated_at,
        )
        try:
            self._alerter.send(event)
            logger.info("Status report sent at %s", report.generated_at)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to send status report: %s", exc)
