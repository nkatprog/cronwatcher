"""Watcher: main polling loop that ties Scheduler and Notifier together."""

from __future__ import annotations

import logging
import time
from typing import Optional

from cronwatcher.alerter import AlertEvent, Alerter
from cronwatcher.config import CronWatcherConfig
from cronwatcher.notifier import Notifier
from cronwatcher.scheduler import Scheduler

logger = logging.getLogger(__name__)


class Watcher:
    """Polls the Scheduler for missed jobs and dispatches alerts via Notifier."""

    def __init__(
        self,
        config: CronWatcherConfig,
        scheduler: Scheduler,
        alerter: Alerter,
        poll_interval: int = 60,
        cooldown_seconds: Optional[int] = None,
    ) -> None:
        self._config = config
        self._scheduler = scheduler
        self._notifier = Notifier(
            alerter=alerter,
            cooldown_seconds=cooldown_seconds if cooldown_seconds is not None else poll_interval * 5,
        )
        self._poll_interval = poll_interval
        self._running = False

    def _check_once(self) -> None:
        """Run a single check cycle across all configured jobs."""
        for job in self._config.jobs:
            missed = self._scheduler.check_missed(job.name)
            if missed:
                event = AlertEvent(
                    job_name=job.name,
                    reason="missed",
                    details=(
                        f"Job '{job.name}' has not reported a heartbeat within "
                        f"the expected interval of {job.interval_seconds}s."
                    ),
                )
                self._notifier.notify(event)
            else:
                # Recovery: clear cooldown so a future miss triggers immediately.
                self._notifier.reset(job.name)

    def run_once(self) -> None:
        """Perform a single check cycle (useful for testing or one-shot mode)."""
        self._check_once()

    def start(self) -> None:
        """Block and poll indefinitely until stop() is called."""
        self._running = True
        logger.info("Watcher started (poll_interval=%ds).", self._poll_interval)
        try:
            while self._running:
                self._check_once()
                time.sleep(self._poll_interval)
        except KeyboardInterrupt:
            logger.info("Watcher interrupted by user.")
        finally:
            self._running = False
            logger.info("Watcher stopped.")

    def stop(self) -> None:
        """Signal the polling loop to stop."""
        self._running = False
