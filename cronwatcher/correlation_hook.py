"""Watcher hook that feeds job events into the JobCorrelationManager."""
from __future__ import annotations

from typing import Optional

from cronwatcher.alerter import AlertEvent, Alerter
from cronwatcher.job_correlation import JobCorrelationManager


class CorrelationHook:
    """Intercepts missed/healthy events and suppresses correlated alerts.

    Usage::

        hook = CorrelationHook(manager, alerter)
        hook.on_missed(event)   # sends alert only when not suppressed
        hook.on_healthy(job_id) # clears correlation state for the job
    """

    def __init__(self, manager: JobCorrelationManager, alerter: Alerter) -> None:
        self._manager = manager
        self._alerter = alerter

    def on_missed(self, event: AlertEvent) -> bool:
        """Record the failure and send an alert unless suppressed.

        Returns True if the alert was sent, False if suppressed.
        """
        self._manager.record_failure(event.job_id)
        if self._manager.is_suppressed(event.job_id):
            return False
        self._alerter.send(event)
        return True

    def on_healthy(self, job_id: str) -> None:
        """Clear the failure record for a recovered job."""
        self._manager.record_recovery(job_id)
