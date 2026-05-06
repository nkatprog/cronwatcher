"""Tests for cronwatcher.history module."""

import json
import os
import pytest
from cronwatcher.history import HistoryEntry, HistoryLog


@pytest.fixture
def log_file(tmp_path):
    return str(tmp_path / "history.json")


@pytest.fixture
def history(log_file):
    return HistoryLog(path=log_file)


class TestHistoryEntry:
    def test_to_dict_roundtrip(self):
        entry = HistoryEntry(
            job_name="backup",
            event_type="missed",
            timestamp="2024-01-01T00:00:00",
            message="overdue by 5 minutes",
        )
        d = entry.to_dict()
        restored = HistoryEntry.from_dict(d)
        assert restored == entry

    def test_from_dict_optional_message(self):
        d = {"job_name": "sync", "event_type": "heartbeat", "timestamp": "2024-01-01T00:00:00"}
        entry = HistoryEntry.from_dict(d)
        assert entry.message is None


class TestHistoryLog:
    def test_record_creates_entry(self, history):
        entry = history.record("backup", "missed", "overdue")
        assert entry.job_name == "backup"
        assert entry.event_type == "missed"
        assert entry.message == "overdue"
        assert entry.timestamp

    def test_record_persists_to_disk(self, log_file, history):
        history.record("sync", "heartbeat")
        with open(log_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["job_name"] == "sync"

    def test_load_existing_file(self, log_file):
        existing = [
            {"job_name": "job1", "event_type": "missed", "timestamp": "2024-01-01T00:00:00", "message": None}
        ]
        with open(log_file, "w") as f:
            json.dump(existing, f)
        log = HistoryLog(path=log_file)
        assert len(log.get_all()) == 1
        assert log.get_all()[0].job_name == "job1"

    def test_get_for_job_filters_correctly(self, history):
        history.record("job_a", "heartbeat")
        history.record("job_b", "missed")
        history.record("job_a", "failure")
        results = history.get_for_job("job_a")
        assert len(results) == 2
        assert all(e.job_name == "job_a" for e in results)

    def test_get_recent_limits_results(self, history):
        for i in range(10):
            history.record(f"job_{i}", "heartbeat")
        recent = history.get_recent(limit=3)
        assert len(recent) == 3
        assert recent[-1].job_name == "job_9"

    def test_max_entries_trimmed(self, log_file):
        log = HistoryLog(path=log_file, max_entries=5)
        for i in range(8):
            log.record("job", "heartbeat")
        assert len(log.get_all()) == 5

    def test_corrupted_file_starts_fresh(self, log_file):
        with open(log_file, "w") as f:
            f.write("not valid json{{")
        log = HistoryLog(path=log_file)
        assert log.get_all() == []
