"""Tests for cronwatcher.cli_audit."""

from __future__ import annotations

import json

import pytest

from cronwatcher.audit import AuditLog
from cronwatcher.cli_audit import build_arg_parser, main


@pytest.fixture()
def log_file(tmp_path):
    path = str(tmp_path / "audit.json")
    log = AuditLog(path)
    log.record("config_loaded", "loaded config.json", actor="daemon")
    log.record("job_missed", "backup missed", actor="daemon")
    log.record("silence_added", "added window", actor="cli")
    return path


class TestCliAudit:
    def test_parser_defaults(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.log == "audit.json"
        assert args.format == "text"
        assert args.event_type is None
        assert args.limit is None

    def test_text_output_all_entries(self, log_file, capsys):
        main(["--log", log_file])
        out = capsys.readouterr().out
        assert "config_loaded" in out
        assert "job_missed" in out
        assert "silence_added" in out

    def test_json_output(self, log_file, capsys):
        main(["--log", log_file, "--format", "json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_filter_by_event_type(self, log_file, capsys):
        main(["--log", log_file, "--event-type", "job_missed"])
        out = capsys.readouterr().out
        assert "job_missed" in out
        assert "config_loaded" not in out

    def test_limit_restricts_output(self, log_file, capsys):
        main(["--log", log_file, "--format", "json", "--limit", "1"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert len(data) == 1
        # --limit returns the *last* N entries
        assert data[0]["event_type"] == "silence_added"

    def test_no_entries_prints_message(self, tmp_path, capsys):
        empty_log = str(tmp_path / "empty.json")
        main(["--log", empty_log])
        out = capsys.readouterr().out
        assert "No audit entries found" in out
