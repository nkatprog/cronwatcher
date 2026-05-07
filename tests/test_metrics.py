"""Tests for cronwatcher.metrics."""

from datetime import datetime

import pytest

from cronwatcher.metrics import JobMetrics, MetricsCollector


@pytest.fixture
def collector() -> MetricsCollector:
    return MetricsCollector()


class TestJobMetrics:
    def test_to_dict_contains_all_keys(self):
        m = JobMetrics(job_name="backup")
        d = m.to_dict()
        assert set(d.keys()) == {
            "job_name", "total_pings", "total_missed",
            "total_alerts_sent", "last_ping_at", "last_missed_at",
        }

    def test_to_dict_serialises_datetime(self):
        ts = datetime(2024, 1, 15, 12, 0, 0)
        m = JobMetrics(job_name="backup", last_ping_at=ts)
        assert m.to_dict()["last_ping_at"] == "2024-01-15T12:00:00"

    def test_to_dict_none_when_no_timestamp(self):
        m = JobMetrics(job_name="backup")
        assert m.to_dict()["last_ping_at"] is None


class TestMetricsCollector:
    def test_record_ping_increments_counter(self, collector):
        collector.record_ping("job_a")
        collector.record_ping("job_a")
        assert collector.get("job_a").total_pings == 2

    def test_record_missed_increments_counter(self, collector):
        collector.record_missed("job_a")
        assert collector.get("job_a").total_missed == 1

    def test_record_alert_increments_counter(self, collector):
        collector.record_alert("job_a")
        assert collector.get("job_a").total_alerts_sent == 1

    def test_get_returns_none_for_unknown_job(self, collector):
        assert collector.get("nonexistent") is None

    def test_record_ping_stores_timestamp(self, collector):
        ts = datetime(2024, 6, 1, 8, 0, 0)
        collector.record_ping("job_b", at=ts)
        assert collector.get("job_b").last_ping_at == ts

    def test_all_returns_all_jobs(self, collector):
        collector.record_ping("job_a")
        collector.record_ping("job_b")
        assert set(collector.all().keys()) == {"job_a", "job_b"}

    def test_summary_returns_list_of_dicts(self, collector):
        collector.record_ping("job_a")
        result = collector.summary()
        assert isinstance(result, list)
        assert result[0]["job_name"] == "job_a"

    def test_independent_counters_per_job(self, collector):
        collector.record_ping("job_a")
        collector.record_missed("job_b")
        assert collector.get("job_a").total_missed == 0
        assert collector.get("job_b").total_pings == 0
