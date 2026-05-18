"""Tests for cronwatcher.job_correlation."""
from datetime import datetime, timedelta

import pytest

from cronwatcher.job_correlation import (
    CorrelationGroup,
    CorrelationState,
    JobCorrelationManager,
)


# ---------------------------------------------------------------------------
# CorrelationGroup
# ---------------------------------------------------------------------------

class TestCorrelationGroup:
    def test_from_dict_valid(self):
        g = CorrelationGroup.from_dict({"name": "db", "job_ids": ["a", "b"], "suppress_after": 2})
        assert g.name == "db"
        assert g.job_ids == ["a", "b"]
        assert g.suppress_after == 2

    def test_from_dict_defaults_suppress_after(self):
        g = CorrelationGroup.from_dict({"name": "x", "job_ids": ["j1"]})
        assert g.suppress_after == 1

    def test_from_dict_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            CorrelationGroup.from_dict({"job_ids": ["a"]})

    def test_from_dict_missing_job_ids_raises(self):
        with pytest.raises(ValueError, match="job_id"):
            CorrelationGroup.from_dict({"name": "g", "job_ids": []})

    def test_from_dict_invalid_suppress_after_raises(self):
        with pytest.raises(ValueError, match="suppress_after"):
            CorrelationGroup.from_dict({"name": "g", "job_ids": ["a"], "suppress_after": 0})

    def test_to_dict_roundtrip(self):
        data = {"name": "g", "job_ids": ["a", "b"], "suppress_after": 3}
        assert CorrelationGroup.from_dict(data).to_dict() == data


# ---------------------------------------------------------------------------
# CorrelationState
# ---------------------------------------------------------------------------

class TestCorrelationState:
    def test_active_failure_count_within_window(self):
        state = CorrelationState()
        state.record_failure("j1")
        state.record_failure("j2")
        assert state.active_failure_count(window_seconds=300) == 2

    def test_old_failures_excluded(self):
        state = CorrelationState()
        old_ts = datetime.utcnow() - timedelta(seconds=400)
        state.record_failure("j1", ts=old_ts)
        state.record_failure("j2")
        assert state.active_failure_count(window_seconds=300) == 1

    def test_clear_removes_entry(self):
        state = CorrelationState()
        state.record_failure("j1")
        state.clear_failure("j1")
        assert state.active_failure_count() == 0

    def test_clear_unknown_job_is_noop(self):
        state = CorrelationState()
        state.clear_failure("unknown")  # should not raise


# ---------------------------------------------------------------------------
# JobCorrelationManager
# ---------------------------------------------------------------------------

@pytest.fixture()
def manager():
    groups = [
        CorrelationGroup(name="infra", job_ids=["backup", "sync", "cleanup"], suppress_after=1)
    ]
    return JobCorrelationManager(groups, window_seconds=300)


class TestJobCorrelationManager:
    def test_not_suppressed_with_no_failures(self, manager):
        assert manager.is_suppressed("backup") is False

    def test_not_suppressed_at_threshold(self, manager):
        manager.record_failure("backup")
        # count == 1, suppress_after == 1 → not suppressed (needs to exceed)
        assert manager.is_suppressed("backup") is False

    def test_suppressed_above_threshold(self, manager):
        manager.record_failure("backup")
        manager.record_failure("sync")
        # count == 2 > suppress_after(1) → suppressed
        assert manager.is_suppressed("cleanup") is True

    def test_recovery_reduces_count(self, manager):
        manager.record_failure("backup")
        manager.record_failure("sync")
        manager.record_recovery("sync")
        assert manager.is_suppressed("cleanup") is False

    def test_job_not_in_any_group_never_suppressed(self, manager):
        manager.record_failure("backup")
        manager.record_failure("sync")
        assert manager.is_suppressed("unknown_job") is False
