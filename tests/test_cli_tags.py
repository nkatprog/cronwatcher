"""Tests for cronwatcher.cli_tags."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli_tags import build_arg_parser, main


@pytest.fixture()
def config_file(tmp_path):
    cfg = {
        "jobs": {
            "backup": {"schedule": "0 2 * * *", "timeout": 60, "tags": ["backup", "nightly"]},
            "deploy": {"schedule": "0 12 * * *", "timeout": 120, "tags": ["critical"]},
            "cleanup": {"schedule": "0 3 * * *", "timeout": 30, "tags": []},
        },
        "alert": {"email": {"to": "ops@example.com", "from": "cron@example.com", "smtp_host": "localhost"}},
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return str(p)


def _fake_cfg(jobs_dict):
    cfg = MagicMock()
    cfg.jobs = {
        name: SimpleNamespace(tags=info.get("tags", []))
        for name, info in jobs_dict.items()
    }
    return cfg


class TestCliTags:
    def test_parser_defaults(self):
        parser = build_arg_parser()
        args = parser.parse_args(["config.json"])
        assert args.include == []
        assert args.exclude == []
        assert args.as_json is False

    def test_parser_include_exclude(self):
        parser = build_arg_parser()
        args = parser.parse_args(["c.json", "--include", "critical", "--exclude", "disabled"])
        assert args.include == ["critical"]
        assert args.exclude == ["disabled"]

    def test_text_output_all_jobs(self, config_file, capsys):
        main([config_file])
        out = capsys.readouterr().out
        assert "backup" in out
        assert "deploy" in out
        assert "cleanup" in out

    def test_text_output_include_filter(self, config_file, capsys):
        main([config_file, "--include", "critical"])
        out = capsys.readouterr().out
        assert "deploy" in out
        assert "backup" not in out

    def test_json_output(self, config_file, capsys):
        main([config_file, "--json"])
        data = json.loads(capsys.readouterr().out)
        names = {item["name"] for item in data}
        assert "backup" in names
        assert "deploy" in names

    def test_no_match_prints_message(self, config_file, capsys):
        main([config_file, "--include", "nonexistent"])
        out = capsys.readouterr().out
        assert "No jobs matched" in out
