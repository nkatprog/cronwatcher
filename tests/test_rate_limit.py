"""Tests for cronwatcher.rate_limit."""

import pytest
from cronwatcher.rate_limit import RateLimiter, RateLimitEntry


WINDOW = 60.0  # seconds
NOW = 1_000_000.0


@pytest.fixture
def limiter() -> RateLimiter:
    return RateLimiter(max_alerts=3, window_seconds=WINDOW)


class TestRateLimiterInit:
    def test_invalid_max_alerts_raises(self):
        with pytest.raises(ValueError, match="max_alerts"):
            RateLimiter(max_alerts=0)

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            RateLimiter(max_alerts=1, window_seconds=0)


class TestRateLimiterAllowed:
    def test_first_alert_is_allowed(self, limiter):
        assert limiter.is_allowed("job_a", now=NOW) is True

    def test_allowed_up_to_max(self, limiter):
        for _ in range(3):
            limiter.record("job_a", now=NOW)
        assert limiter.is_allowed("job_a", now=NOW) is False

    def test_different_jobs_are_independent(self, limiter):
        for _ in range(3):
            limiter.record("job_a", now=NOW)
        assert limiter.is_allowed("job_b", now=NOW) is True

    def test_window_expiry_resets_count(self, limiter):
        for _ in range(3):
            limiter.record("job_a", now=NOW)
        assert limiter.is_allowed("job_a", now=NOW) is False
        # Advance past the window
        assert limiter.is_allowed("job_a", now=NOW + WINDOW + 1) is True


class TestRateLimiterRecord:
    def test_record_increments_count(self, limiter):
        limiter.record("job_a", now=NOW)
        assert limiter.remaining("job_a", now=NOW) == 2

    def test_record_sets_last_sent(self, limiter):
        limiter.record("job_a", now=NOW)
        entry = limiter._entries["job_a"]
        assert entry.last_sent == NOW

    def test_record_resets_on_new_window(self, limiter):
        for _ in range(3):
            limiter.record("job_a", now=NOW)
        # Record in new window — should reset then count 1
        limiter.record("job_a", now=NOW + WINDOW + 1)
        assert limiter.remaining("job_a", now=NOW + WINDOW + 1) == 2


class TestRateLimiterRemaining:
    def test_remaining_starts_at_max(self, limiter):
        assert limiter.remaining("job_x", now=NOW) == 3

    def test_remaining_decreases_after_record(self, limiter):
        limiter.record("job_x", now=NOW)
        limiter.record("job_x", now=NOW)
        assert limiter.remaining("job_x", now=NOW) == 1

    def test_remaining_zero_when_exhausted(self, limiter):
        for _ in range(5):  # more than max
            limiter.record("job_x", now=NOW)
        assert limiter.remaining("job_x", now=NOW) == 0


class TestRateLimiterResetJob:
    def test_reset_clears_entry(self, limiter):
        for _ in range(3):
            limiter.record("job_a", now=NOW)
        limiter.reset_job("job_a")
        assert limiter.is_allowed("job_a", now=NOW) is True

    def test_reset_unknown_job_is_safe(self, limiter):
        limiter.reset_job("nonexistent")  # should not raise
