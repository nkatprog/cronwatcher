"""Tests for cronwatcher.job_timeout."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatcher.job_timeout import JobTimeoutTracker, TimeoutViolation


def _make_job(name: str, timeout_seconds: int):
    job = MagicMock()
    job.name = name
    job.timeout_seconds = timeout_seconds
    return job


@pytest.fixture()
def tracker():
    return JobTimeoutTracker()


class TestTimeoutViolationStr:
    def test_str_contains_job_name(self):
        v = TimeoutViolation(
            job_name="backup",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            timeout_seconds=300,
            elapsed_seconds=450.0,
        )
        assert "backup" in str(v)
        assert "300" in str(v)
        assert "450.0" in str(v)


class TestJobTimeoutTracker:
    def test_record_start_stores_timestamp(self, tracker):
        t = datetime(2024, 6, 1, 10, 0, 0)
        tracker.record_start("myjob", started_at=t)
        assert tracker.started_at("myjob") == t

    def test_record_start_defaults_to_utcnow(self, tracker):
        before = datetime.utcnow()
        tracker.record_start("myjob")
        after = datetime.utcnow()
        ts = tracker.started_at("myjob")
        assert before <= ts <= after

    def test_record_finish_removes_entry(self, tracker):
        tracker.record_start("myjob")
        tracker.record_finish("myjob")
        assert tracker.started_at("myjob") is None

    def test_record_finish_unknown_job_is_noop(self, tracker):
        tracker.record_finish("ghost")  # should not raise

    def test_no_violations_when_within_timeout(self, tracker):
        now = datetime(2024, 6, 1, 12, 0, 0)
        tracker.record_start("backup", started_at=now - timedelta(seconds=100))
        jobs = [_make_job("backup", timeout_seconds=300)]
        violations = tracker.check_timeouts(jobs, now=now)
        assert violations == []

    def test_violation_when_timeout_exceeded(self, tracker):
        now = datetime(2024, 6, 1, 12, 0, 0)
        tracker.record_start("backup", started_at=now - timedelta(seconds=400))
        jobs = [_make_job("backup", timeout_seconds=300)]
        violations = tracker.check_timeouts(jobs, now=now)
        assert len(violations) == 1
        v = violations[0]
        assert v.job_name == "backup"
        assert v.timeout_seconds == 300
        assert v.elapsed_seconds == pytest.approx(400.0)

    def test_no_violation_for_job_without_timeout_config(self, tracker):
        now = datetime(2024, 6, 1, 12, 0, 0)
        tracker.record_start("backup", started_at=now - timedelta(seconds=9999))
        job = MagicMock()
        job.name = "backup"
        job.timeout_seconds = None
        violations = tracker.check_timeouts([job], now=now)
        assert violations == []

    def test_multiple_violations_returned(self, tracker):
        now = datetime(2024, 6, 1, 12, 0, 0)
        tracker.record_start("jobA", started_at=now - timedelta(seconds=600))
        tracker.record_start("jobB", started_at=now - timedelta(seconds=800))
        jobs = [_make_job("jobA", 300), _make_job("jobB", 300)]
        violations = tracker.check_timeouts(jobs, now=now)
        names = {v.job_name for v in violations}
        assert names == {"jobA", "jobB"}

    def test_finished_job_not_checked(self, tracker):
        now = datetime(2024, 6, 1, 12, 0, 0)
        tracker.record_start("backup", started_at=now - timedelta(seconds=400))
        tracker.record_finish("backup")
        jobs = [_make_job("backup", timeout_seconds=300)]
        violations = tracker.check_timeouts(jobs, now=now)
        assert violations == []
