"""Webhook delivery with configurable retry logic."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_base: float = 2.0  # seconds; delay = backoff_base ** attempt
    max_delay: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff_base <= 0:
            raise ValueError("backoff_base must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")

    def delay_for(self, attempt: int) -> float:
        """Return sleep duration (seconds) before *attempt* (0-indexed)."""
        if attempt == 0:
            return 0.0
        return min(self.backoff_base ** attempt, self.max_delay)


@dataclass
class DeliveryResult:
    success: bool
    attempts: int
    last_status: Optional[int] = None
    errors: List[str] = field(default_factory=list)


class WebhookRetrier:
    """Wraps a callable that performs a single HTTP POST and retries on failure."""

    def __init__(
        self,
        policy: Optional[RetryPolicy] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._policy = policy or RetryPolicy()
        self._sleep = sleep_fn

    def deliver(
        self,
        send_fn: Callable[[], int],
    ) -> DeliveryResult:
        """Call *send_fn* which returns an HTTP status code.

        Retries on non-2xx responses or exceptions according to the policy.
        Returns a :class:`DeliveryResult` summarising the outcome.
        """
        errors: List[str] = []
        last_status: Optional[int] = None

        for attempt in range(self._policy.max_attempts):
            delay = self._policy.delay_for(attempt)
            if delay > 0:
                logger.debug("Webhook retry: sleeping %.1fs before attempt %d", delay, attempt + 1)
                self._sleep(delay)

            try:
                status = send_fn()
                last_status = status
                if 200 <= status < 300:
                    logger.debug("Webhook delivered on attempt %d (status %d)", attempt + 1, status)
                    return DeliveryResult(success=True, attempts=attempt + 1, last_status=status, errors=errors)
                msg = f"Non-2xx status {status} on attempt {attempt + 1}"
                logger.warning(msg)
                errors.append(msg)
            except Exception as exc:  # noqa: BLE001
                msg = f"Exception on attempt {attempt + 1}: {exc}"
                logger.warning(msg)
                errors.append(msg)

        return DeliveryResult(success=False, attempts=self._policy.max_attempts, last_status=last_status, errors=errors)
