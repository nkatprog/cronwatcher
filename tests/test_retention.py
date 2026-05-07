"""Tests for cronwatcher.retention module."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from cronwatcher.history import HistoryEntry, HistoryLog
from cronwatcher.retention import HistoryPruner, RetentionPolicy


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
OLD = NOW - timedelta(days=40)
RECENT = NOW - timedelta(days=5)


@pytest.fixture
def history(tmp_path):
    log = HistoryLog(str(tmp_path / "history.json"))
    log._entries = {
        "backup": [
            HistoryEntry(job_name="backup", timestamp=OLD, success=True),
            HistoryEntry(job_name="backup", timestamp=RECENT, success=True),
        ],
        "cleanup": [
            HistoryEntry(job_name="cleanup", timestamp=OLD, success=False, message="err"),
        ],
    }
    return log


class TestRetentionPolicy:
    def test_cutoff_is_max_age_days_ago(self):
        policy = RetentionPolicy(max_age_days=30)
        with patch("cronwatcher.retention.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            cutoff = policy.cutoff_time()
        assert cutoff == NOW - timedelta(days=30)

    def test_invalid_max_age_raises(self):
        with pytest.raises(ValueError):
            RetentionPolicy(max_age_days=0)


class TestHistoryPruner:
    def test_prune_removes_old_entries(self, history):
        policy = RetentionPolicy(max_age_days=30)
        pruner = HistoryPruner(history, policy)
        with patch("cronwatcher.retention.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            removed = pruner.prune()
        assert removed == 2
        assert len(history._entries["backup"]) == 1
        assert history._entries["backup"][0].timestamp == RECENT
        assert len(history._entries["cleanup"]) == 0

    def test_prune_keeps_recent_entries(self, history):
        policy = RetentionPolicy(max_age_days=60)
        pruner = HistoryPruner(history, policy)
        with patch("cronwatcher.retention.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            removed = pruner.prune()
        assert removed == 0

    def test_prune_respects_max_entries(self, history):
        history._entries["backup"] = [
            HistoryEntry(job_name="backup", timestamp=RECENT + timedelta(seconds=i), success=True)
            for i in range(5)
        ]
        policy = RetentionPolicy(max_age_days=60, max_entries_per_job=3)
        pruner = HistoryPruner(history, policy)
        with patch("cronwatcher.retention.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            removed = pruner.prune()
        assert removed == 2
        assert len(history._entries["backup"]) == 3

    def test_prune_saves_when_entries_removed(self, history):
        history.save = MagicMock()
        policy = RetentionPolicy(max_age_days=30)
        pruner = HistoryPruner(history, policy)
        with patch("cronwatcher.retention.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            pruner.prune()
        history.save.assert_called_once()

    def test_prune_no_save_when_nothing_removed(self, history):
        history.save = MagicMock()
        policy = RetentionPolicy(max_age_days=60)
        pruner = HistoryPruner(history, policy)
        with patch("cronwatcher.retention.datetime") as mock_dt:
            mock_dt.now.return_value = NOW
            pruner.prune()
        history.save.assert_not_called()
