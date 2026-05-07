"""Tests for cronwatcher.audit."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from cronwatcher.audit import AuditEntry, AuditLog


@pytest.fixture()
def log_file(tmp_path):
    return str(tmp_path / "audit.json")


@pytest.fixture()
def audit(log_file):
    return AuditLog(log_file)


# ------------------------------------------------------------------ #
#  AuditEntry                                                          #
# ------------------------------------------------------------------ #

class TestAuditEntry:
    def test_to_dict_roundtrip(self):
        now = datetime.now(tz=timezone.utc)
        entry = AuditEntry(
            timestamp=now,
            event_type="config_loaded",
            actor="daemon",
            detail="loaded config.json",
            extra={"jobs": 3},
        )
        restored = AuditEntry.from_dict(entry.to_dict())
        assert restored.event_type == entry.event_type
        assert restored.actor == entry.actor
        assert restored.detail == entry.detail
        assert restored.extra == {"jobs": 3}

    def test_from_dict_no_extra(self):
        data = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "event_type": "job_missed",
            "actor": "daemon",
            "detail": "backup missed",
        }
        entry = AuditEntry.from_dict(data)
        assert entry.extra == {}


# ------------------------------------------------------------------ #
#  AuditLog                                                            #
# ------------------------------------------------------------------ #

class TestAuditLog:
    def test_record_returns_entry(self, audit):
        entry = audit.record("config_loaded", "loaded config.json")
        assert entry.event_type == "config_loaded"
        assert entry.actor == "daemon"

    def test_record_persists_to_disk(self, audit, log_file):
        audit.record("silence_added", "added window for backup", actor="cli")
        with open(log_file) as fh:
            data = json.load(fh)
        assert len(data) == 1
        assert data[0]["event_type"] == "silence_added"

    def test_all_entries_returns_all(self, audit):
        audit.record("config_loaded", "a")
        audit.record("job_missed", "b")
        assert len(audit.all_entries()) == 2

    def test_entries_for_filters_by_type(self, audit):
        audit.record("config_loaded", "a")
        audit.record("job_missed", "b")
        audit.record("job_missed", "c")
        missed = audit.entries_for("job_missed")
        assert len(missed) == 2

    def test_entries_for_unknown_type_returns_empty(self, audit):
        audit.record("config_loaded", "a")
        assert audit.entries_for("nonexistent") == []

    def test_load_from_existing_file(self, log_file):
        """A second AuditLog instance reads entries written by the first."""
        first = AuditLog(log_file)
        first.record("config_loaded", "initial load")

        second = AuditLog(log_file)
        assert len(second.all_entries()) == 1
        assert second.all_entries()[0].event_type == "config_loaded"

    def test_missing_file_starts_empty(self, log_file):
        assert not os.path.exists(log_file)
        audit = AuditLog(log_file)
        assert audit.all_entries() == []
