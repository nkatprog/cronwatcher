"""Watcher hook that drives the EscalationManager on each check cycle."""

from __future__ import annotations

from typing import List

from cronwatcher.alerter import AlertEvent, Alerter
from cronwatcher.escalation import EscalationManager


class EscalationHook:
    """Integrates EscalationManager with the Watcher check cycle.

    Call :meth:`on_missed` when a job is detected as missed/failed and
    :meth:`on_healthy` when it recovers.  The hook will dispatch escalation
    alerts via *alerter* to the appropriate contacts.
    """

    def __init__(self, manager: EscalationManager, alerter: Alerter) -> None:
        self._manager = manager
        self._alerter = alerter

    def on_missed(self, job_name: str) -> List[str]:
        """Record a failure and send escalation alerts if thresholds are met.

        Returns the list of contacts that were notified (may be empty).
        """
        self._manager.record_failure(job_name)
        contacts = self._manager.contacts_to_notify(job_name)
        if contacts:
            event = AlertEvent(
                job_name=job_name,
                reason="missed",
                message=(
                    f"Job '{job_name}' has missed "
                    f"{self._manager.consecutive_failures(job_name)} consecutive run(s). "
                    "Escalating to additional contacts."
                ),
            )
            for contact in contacts:
                self._alerter.send(event, override_target=contact)
            self._manager.mark_escalated(job_name, contacts)
        return contacts

    def on_healthy(self, job_name: str) -> None:
        """Record a recovery, resetting the failure counter."""
        self._manager.record_recovery(job_name)
