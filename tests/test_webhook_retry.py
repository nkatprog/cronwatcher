"""Tests for cronwatcher.webhook_retry."""
from __future__ import annotations

import pytest

from cronwatcher.webhook_retry import DeliveryResult, RetryPolicy, WebhookRetrier


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

class TestRetryPolicy:
    def test_delay_zero_for_first_attempt(self):
        policy = RetryPolicy(backoff_base=2.0)
        assert policy.delay_for(0) == 0.0

    def test_delay_exponential(self):
        policy = RetryPolicy(backoff_base=2.0, max_delay=100.0)
        assert policy.delay_for(1) == 2.0
        assert policy.delay_for(2) == 4.0
        assert policy.delay_for(3) == 8.0

    def test_delay_capped_at_max(self):
        policy = RetryPolicy(backoff_base=2.0, max_delay=5.0)
        assert policy.delay_for(10) == 5.0

    def test_invalid_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryPolicy(max_attempts=0)

    def test_invalid_backoff_raises(self):
        with pytest.raises(ValueError, match="backoff_base"):
            RetryPolicy(backoff_base=0)

    def test_invalid_max_delay_raises(self):
        with pytest.raises(ValueError, match="max_delay"):
            RetryPolicy(max_delay=-1)


# ---------------------------------------------------------------------------
# WebhookRetrier helpers
# ---------------------------------------------------------------------------

def _no_sleep(seconds: float) -> None:  # noqa: ARG001
    pass


def _make_retrier(max_attempts: int = 3, backoff_base: float = 2.0) -> WebhookRetrier:
    return WebhookRetrier(policy=RetryPolicy(max_attempts=max_attempts, backoff_base=backoff_base), sleep_fn=_no_sleep)


# ---------------------------------------------------------------------------
# WebhookRetrier
# ---------------------------------------------------------------------------

class TestWebhookRetrier:
    def test_success_on_first_attempt(self):
        retrier = _make_retrier()
        result = retrier.deliver(lambda: 200)
        assert result.success is True
        assert result.attempts == 1
        assert result.last_status == 200

    def test_success_on_second_attempt(self):
        calls = iter([500, 204])
        retrier = _make_retrier()
        result = retrier.deliver(lambda: next(calls))
        assert result.success is True
        assert result.attempts == 2
        assert result.last_status == 204

    def test_failure_after_all_attempts(self):
        retrier = _make_retrier(max_attempts=3)
        result = retrier.deliver(lambda: 503)
        assert result.success is False
        assert result.attempts == 3
        assert result.last_status == 503
        assert len(result.errors) == 3

    def test_exception_is_caught_and_retried(self):
        calls = [0]

        def flaky() -> int:
            calls[0] += 1
            if calls[0] < 3:
                raise ConnectionError("timeout")
            return 200

        retrier = _make_retrier(max_attempts=3)
        result = retrier.deliver(flaky)
        assert result.success is True
        assert result.attempts == 3
        assert len(result.errors) == 2

    def test_all_exceptions_returns_failure(self):
        retrier = _make_retrier(max_attempts=2)
        result = retrier.deliver(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert result.success is False
        assert result.attempts == 2

    def test_sleep_called_with_correct_delays(self):
        slept: list[float] = []
        retrier = WebhookRetrier(
            policy=RetryPolicy(max_attempts=3, backoff_base=2.0, max_delay=100.0),
            sleep_fn=slept.append,
        )
        retrier.deliver(lambda: 500)
        # First attempt: no sleep; second: 2.0s; third: 4.0s
        assert slept == [2.0, 4.0]
