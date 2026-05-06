import pytest
from datetime import datetime, timedelta
from cronwatcher.config import JobConfig
from cronwatcher.scheduler import JobState, Scheduler


@pytest.fixture
def sample_job():
    return JobConfig(name="backup", interval_seconds=3600, grace_seconds=300)


@pytest.fixture
def scheduler(sample_job):
    extra_job = JobConfig(name="cleanup", interval_seconds=600, grace_seconds=60)
    return Scheduler(jobs=[sample_job, extra_job])


class TestJobState:
    def test_no_missed_without_heartbeat(self, sample_job):
        state = JobState(sample_job)
        assert state.check_missed() is False

    def test_not_missed_within_window(self, sample_job):
        state = JobState(sample_job)
        now = datetime(2024, 1, 1, 12, 0, 0)
        state.record_heartbeat(now)
        check_time = now + timedelta(seconds=3600)
        assert state.check_missed(check_time) is False

    def test_missed_after_interval_plus_grace(self, sample_job):
        state = JobState(sample_job)
        now = datetime(2024, 1, 1, 12, 0, 0)
        state.record_heartbeat(now)
        check_time = now + timedelta(seconds=3600 + 300 + 1)
        assert state.check_missed(check_time) is True

    def test_missed_count_increments_once_per_miss(self, sample_job):
        state = JobState(sample_job)
        now = datetime(2024, 1, 1, 12, 0, 0)
        state.record_heartbeat(now)
        late = now + timedelta(seconds=4100)
        state.check_missed(late)
        state.check_missed(late + timedelta(seconds=60))
        assert state.missed_count == 1

    def test_heartbeat_clears_missed_flag(self, sample_job):
        state = JobState(sample_job)
        now = datetime(2024, 1, 1, 12, 0, 0)
        state.record_heartbeat(now)
        late = now + timedelta(seconds=4100)
        state.check_missed(late)
        assert state.is_missed is True
        state.record_heartbeat(late)
        assert state.is_missed is False


class TestScheduler:
    def test_heartbeat_known_job(self, scheduler):
        assert scheduler.heartbeat("backup") is True

    def test_heartbeat_unknown_job(self, scheduler):
        assert scheduler.heartbeat("nonexistent") is False

    def test_check_all_no_missed(self, scheduler):
        now = datetime(2024, 1, 1, 12, 0, 0)
        scheduler.heartbeat("backup", now)
        scheduler.heartbeat("cleanup", now)
        missed = scheduler.check_all(now + timedelta(seconds=10))
        assert missed == []

    def test_check_all_detects_missed(self, scheduler):
        now = datetime(2024, 1, 1, 12, 0, 0)
        scheduler.heartbeat("backup", now)
        scheduler.heartbeat("cleanup", now)
        late = now + timedelta(seconds=700)
        missed = scheduler.check_all(late)
        assert "cleanup" in missed
        assert "backup" not in missed

    def test_get_state_returns_correct_state(self, scheduler):
        state = scheduler.get_state("backup")
        assert state is not None
        assert state.job.name == "backup"

    def test_get_state_unknown_returns_none(self, scheduler):
        assert scheduler.get_state("ghost") is None
