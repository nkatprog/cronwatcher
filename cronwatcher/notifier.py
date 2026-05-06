"""Notifier module: aggregates alert events and manages notification cooldown/deduplication."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from cronwatcher.alerter import AlertEvent, Alerter

logger = logging.getLogger(__name__)


@dataclass
class NotificationState:
    """Tracks per-job notification history."""
    job_name: str
    last_notified_at: Optional[float] = None
    notification_count: int = 0

    def should_notify(self, cooldown_seconds: int) -> bool:
        """Return True if enough time has passed since the last notification."""
        if self.last_notified_at is None:
            return True
        return (time.time() - self.last_notified_at) >= cooldown_seconds

    def record_notification(self) -> None:
        self.last_notified_at = time.time()
        self.notification_count += 1


class Notifier:
    """Wraps Alerter with cooldown and deduplication logic."""

    def __init__(self, alerter: Alerter, cooldown_seconds: int = 300) -> None:
        self._alerter = alerter
        self._cooldown_seconds = cooldown_seconds
        self._states: Dict[str, NotificationState] = {}

    def _get_state(self, job_name: str) -> NotificationState:
        if job_name not in self._states:
            self._states[job_name] = NotificationState(job_name=job_name)
        return self._states[job_name]

    def notify(self, event: AlertEvent) -> bool:
        """Send a notification if cooldown has elapsed. Returns True if sent."""
        state = self._get_state(event.job_name)
        if not state.should_notify(self._cooldown_seconds):
            logger.debug(
                "Skipping notification for '%s': cooldown active (%ds remaining).",
                event.job_name,
                self._cooldown_seconds - int(time.time() - (state.last_notified_at or 0)),
            )
            return False

        try:
            self._alerter.send(event)
            state.record_notification()
            logger.info("Notification sent for job '%s' (reason: %s).", event.job_name, event.reason)
            return True
        except Exception:
            logger.exception("Failed to send notification for job '%s'.", event.job_name)
            return False

    def reset(self, job_name: str) -> None:
        """Clear notification state for a job (e.g., after recovery)."""
        self._states.pop(job_name, None)
        logger.debug("Notification state reset for job '%s'.", job_name)
