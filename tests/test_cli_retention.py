"""Tests for cronwatcher.cli_retention CLI tool."""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch

from cronwatcher.cli_retention import build_arg_parser, main


@pytest.fixture
def config_file(tmp_path):
    cfg = {
        "jobs": [],
        "alert": {"method": "email", "recipients": []},
        "history_file": str(tmp_path / "history.json"),
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return str(p)


class TestCliRetention:
    def test_parser_defaults(self):
        """Verify that the argument parser sets sensible defaults."""
        parser = build_arg_parser()
        args = parser.parse_args(["--config", "cfg.json"])
        assert args.max_age_days == 30
        assert args.max_entries == 100
        assert not args.dry_run

    def test_parser_custom_values(self):
        """Verify that custom CLI arguments are parsed correctly."""
        parser = build_arg_parser()
        args = parser.parse_args(
            ["--config", "cfg.json", "--max-age-days", "14", "--max-entries", "50", "--dry-run"]
        )
        assert args.max_age_days == 14
        assert args.max_entries == 50
        assert args.dry_run

    def test_prune_calls_pruner(self, config_file, capsys):
        with patch("cronwatcher.cli_retention.HistoryPruner") as MockPruner:
            instance = MockPruner.return_value
            instance.prune.return_value = 7
            with patch("cronwatcher.cli_retention.HistoryLog") as MockLog:
                MockLog.return_value._entries = {}
                main(["--config", config_file])
        out = capsys.readouterr().out
        assert "7" in out

    def test_dry_run_does_not_prune(self, config_file, capsys):
        with patch("cronwatcher.cli_retention.HistoryLog") as MockLog:
            mock_log = MockLog.return_value
            mock_log._entries = {}
            mock_log.load = MagicMock()
            with patch("cronwatcher.cli_retention.HistoryPruner") as MockPruner:
                with pytest.raises(SystemExit) as exc_info:
                    main(["--config", config_file, "--dry-run"])
                assert exc_info.value.code == 0
                MockPruner.return_value.prune.assert_not_called()
        out = capsys.readouterr().out
        assert "Dry run" in out

    def test_unlimited_entries_when_zero(self, config_file):
        with patch("cronwatcher.cli_retention.RetentionPolicy") as MockPolicy:
            MockPolicy.return_value = MagicMock()
            MockPolicy.return_value.cutoff_time.return_value = MagicMock()
            with patch("cronwatcher.cli_retention.HistoryLog"):
                with patch("cronwatcher.cli_retention.HistoryPruner") as MockPruner:
                    MockPruner.return_value.prune.return_value = 0
                    main(["--config", config_file, "--max-entries", "0"])
            _, kwargs = MockPolicy.call_args
            assert kwargs.get("max_entries_per_job") is None or MockPolicy.call_args[1].get("max_entries_per_job") is None
