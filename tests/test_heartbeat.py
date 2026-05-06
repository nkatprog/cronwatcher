"""Tests for HeartbeatReceiver."""

import time
import pytest
from unittest.mock import MagicMock, patch

from cronwatcher.heartbeat import HeartbeatReceiver, HeartbeatRecord


@pytest.fixture
def mock_scheduler():
    scheduler = MagicMock()
    scheduler.jobs = {"backup": MagicMock(), "sync": MagicMock()}
    return scheduler


@pytest.fixture
def receiver(mock_scheduler):
    return HeartbeatReceiver(scheduler=mock_scheduler)


class TestHeartbeatReceiver:
    def test_ping_returns_record(self, receiver):
        record = receiver.ping("backup")
        assert isinstance(record, HeartbeatRecord)
        assert record.job_name == "backup"

    def test_ping_records_timestamp(self, receiver):
        before = time.time()
        record = receiver.ping("backup")
        after = time.time()
        assert before <= record.received_at <= after

    def test_ping_calls_scheduler_record_heartbeat(self, receiver, mock_scheduler):
        record = receiver.ping("backup")
        mock_scheduler.record_heartbeat.assert_called_once_with("backup", record.received_at)

    def test_ping_unknown_job_raises(self, receiver):
        with pytest.raises(ValueError, match="Unknown job: 'nonexistent'"):
            receiver.ping("nonexistent")

    def test_ping_stores_metadata(self, receiver):
        meta = {"exit_code": "0", "host": "worker-1"}
        record = receiver.ping("backup", metadata=meta)
        assert record.metadata == meta

    def test_last_ping_none_before_any_ping(self, receiver):
        assert receiver.last_ping("backup") is None

    def test_last_ping_returns_most_recent(self, receiver):
        receiver.ping("backup")
        r2 = receiver.ping("backup")
        assert receiver.last_ping("backup") is r2

    def test_history_accumulates(self, receiver):
        receiver.ping("backup")
        receiver.ping("backup")
        receiver.ping("sync")
        assert len(receiver.history("backup")) == 2
        assert len(receiver.history("sync")) == 1

    def test_history_empty_for_unknown_job(self, receiver):
        assert receiver.history("never_pinged") == []

    def test_history_returns_copy(self, receiver):
        receiver.ping("backup")
        h = receiver.history("backup")
        h.clear()
        assert len(receiver.history("backup")) == 1
