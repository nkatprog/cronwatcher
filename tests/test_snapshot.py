"""Tests for cronwatcher.snapshot."""
from __future__ import annotations

import json
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from cronwatcher.snapshot import JobSnapshot, StateSnapshot, SnapshotManager


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def snap_file(tmp_path):
    return str(tmp_path / "snapshot.json")


@pytest.fixture
def manager(snap_file):
    return SnapshotManager(snap_file)


class TestJobSnapshot:
    def test_to_dict_with_heartbeat(self):
        js = JobSnapshot("backup", NOW, missed=False, consecutive_misses=0)
        d = js.to_dict()
        assert d["job_name"] == "backup"
        assert d["last_heartbeat"] == NOW.isoformat()
        assert d["missed"] is False

    def test_to_dict_no_heartbeat(self):
        js = JobSnapshot("backup", None, missed=True, consecutive_misses=3)
        assert js.to_dict()["last_heartbeat"] is None

    def test_roundtrip(self):
        js = JobSnapshot("nightly", NOW, missed=True, consecutive_misses=2)
        assert JobSnapshot.from_dict(js.to_dict()) == js

    def test_from_dict_no_heartbeat(self):
        d = {"job_name": "x", "last_heartbeat": None, "missed": False, "consecutive_misses": 0}
        js = JobSnapshot.from_dict(d)
        assert js.last_heartbeat is None


class TestStateSnapshot:
    def test_to_dict_roundtrip(self):
        js = JobSnapshot("j1", NOW, False, 0)
        snap = StateSnapshot(captured_at=NOW, jobs=[js])
        restored = StateSnapshot.from_dict(snap.to_dict())
        assert restored.captured_at == NOW
        assert len(restored.jobs) == 1
        assert restored.jobs[0].job_name == "j1"

    def test_empty_jobs(self):
        snap = StateSnapshot(captured_at=NOW)
        assert snap.to_dict()["jobs"] == []


class TestSnapshotManager:
    def test_load_returns_none_when_missing(self, manager):
        assert manager.load() is None

    def test_save_and_load(self, manager):
        snap = StateSnapshot(captured_at=NOW, jobs=[
            JobSnapshot("db_backup", NOW, False, 0)
        ])
        manager.save(snap)
        loaded = manager.load()
        assert loaded is not None
        assert loaded.captured_at == NOW
        assert loaded.jobs[0].job_name == "db_backup"

    def test_save_is_atomic(self, manager, snap_file):
        """Temp file should not remain after save."""
        snap = StateSnapshot(captured_at=NOW)
        manager.save(snap)
        assert not os.path.exists(snap_file + ".tmp")

    def test_capture_builds_snapshot(self, manager):
        state = MagicMock()
        state.last_heartbeat = NOW
        state.consecutive_misses = 1
        state.check_missed.return_value = True

        scheduler = MagicMock()
        scheduler.states = {"myjob": state}

        snap = manager.capture(scheduler)
        assert len(snap.jobs) == 1
        assert snap.jobs[0].job_name == "myjob"
        assert snap.jobs[0].missed is True
        assert snap.jobs[0].consecutive_misses == 1
