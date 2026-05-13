"""Tests for cronwatcher.cli_snapshot."""
from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from cronwatcher.snapshot import JobSnapshot, StateSnapshot, SnapshotManager
from cronwatcher.cli_snapshot import build_arg_parser, main


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def snap_file(tmp_path):
    path = str(tmp_path / "snapshot.json")
    snap = StateSnapshot(
        captured_at=NOW,
        jobs=[
            JobSnapshot("job_a", NOW, missed=False, consecutive_misses=0),
            JobSnapshot("job_b", None, missed=True, consecutive_misses=2),
        ],
    )
    SnapshotManager(path).save(snap)
    return path


class TestCliSnapshot:
    def test_parser_defaults(self):
        parser = build_arg_parser()
        args = parser.parse_args(["snap.json"])
        assert args.format == "text"
        assert args.missed_only is False

    def test_text_output_returns_zero(self, snap_file, capsys):
        rc = main([snap_file])
        assert rc == 0
        out = capsys.readouterr().out
        assert "job_a" in out
        assert "job_b" in out

    def test_json_output(self, snap_file, capsys):
        rc = main([snap_file, "--format", "json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        names = [j["job_name"] for j in data["jobs"]]
        assert "job_a" in names
        assert "job_b" in names

    def test_missed_only_filters(self, snap_file, capsys):
        rc = main([snap_file, "--missed-only"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "job_b" in out
        assert "job_a" not in out

    def test_missing_file_returns_one(self, tmp_path, capsys):
        rc = main([str(tmp_path / "no_such.json")])
        assert rc == 1
