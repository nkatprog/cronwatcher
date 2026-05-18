"""Tests for cronwatcher.job_priority."""
import pytest

from cronwatcher.job_priority import (
    JobPriorityMap,
    Priority,
    minimum_priority_filter,
)


class TestPriorityFromStr:
    def test_valid_lowercase(self):
        assert Priority.from_str("high") == Priority.HIGH

    def test_valid_uppercase(self):
        assert Priority.from_str("CRITICAL") == Priority.CRITICAL

    def test_valid_mixed_case(self):
        assert Priority.from_str("Medium") == Priority.MEDIUM

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown priority"):
            Priority.from_str("urgent")

    def test_ordering(self):
        assert Priority.LOW < Priority.MEDIUM < Priority.HIGH < Priority.CRITICAL


@pytest.fixture()
def pmap() -> JobPriorityMap:
    return JobPriorityMap()


class TestJobPriorityMap:
    def test_default_is_medium(self, pmap):
        assert pmap.get("unknown-job") == Priority.MEDIUM

    def test_set_and_get(self, pmap):
        pmap.set("backup", Priority.HIGH)
        assert pmap.get("backup") == Priority.HIGH

    def test_overwrite(self, pmap):
        pmap.set("backup", Priority.LOW)
        pmap.set("backup", Priority.CRITICAL)
        assert pmap.get("backup") == Priority.CRITICAL

    def test_remove(self, pmap):
        pmap.set("backup", Priority.HIGH)
        pmap.remove("backup")
        assert pmap.get("backup") == Priority.MEDIUM

    def test_remove_missing_is_noop(self, pmap):
        pmap.remove("nonexistent")  # should not raise

    def test_all_returns_copy(self, pmap):
        pmap.set("a", Priority.LOW)
        pmap.set("b", Priority.HIGH)
        result = pmap.all()
        assert result == {"a": Priority.LOW, "b": Priority.HIGH}
        result["c"] = Priority.CRITICAL
        assert "c" not in pmap.all()

    def test_empty_job_id_raises(self, pmap):
        with pytest.raises(ValueError):
            pmap.set("", Priority.HIGH)

    def test_to_dict(self, pmap):
        pmap.set("job1", Priority.CRITICAL)
        assert pmap.to_dict() == {"job1": "critical"}

    def test_from_dict_roundtrip(self, pmap):
        pmap.set("job1", Priority.LOW)
        pmap.set("job2", Priority.HIGH)
        restored = JobPriorityMap.from_dict(pmap.to_dict())
        assert restored.get("job1") == Priority.LOW
        assert restored.get("job2") == Priority.HIGH

    def test_from_dict_invalid_priority_raises(self):
        with pytest.raises(ValueError):
            JobPriorityMap.from_dict({"job1": "super-urgent"})


class TestMinimumPriorityFilter:
    def test_passes_when_equal(self):
        pmap = JobPriorityMap()
        pmap.set("job", Priority.HIGH)
        assert minimum_priority_filter("job", pmap, Priority.HIGH) is True

    def test_passes_when_above(self):
        pmap = JobPriorityMap()
        pmap.set("job", Priority.CRITICAL)
        assert minimum_priority_filter("job", pmap, Priority.HIGH) is True

    def test_blocked_when_below(self):
        pmap = JobPriorityMap()
        pmap.set("job", Priority.LOW)
        assert minimum_priority_filter("job", pmap, Priority.HIGH) is False

    def test_uses_default_medium_for_unknown_job(self):
        pmap = JobPriorityMap()
        assert minimum_priority_filter("unknown", pmap, Priority.LOW) is True
        assert minimum_priority_filter("unknown", pmap, Priority.HIGH) is False
