"""Tests for cronwatcher.reporter."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.history import HistoryEntry, HistoryLog
from cronwatcher.reporter import Reporter, StatusReport


def _entry(job: str, status: str, ts: datetime) -> HistoryEntry:
    return HistoryEntry(job_name=job, status=status, timestamp=ts, message=None)


@pytest.fixture()
def mock_scheduler():
    sched = MagicMock()
    sched.job_names.return_value = ["backup", "cleanup"]
    return sched


@pytest.fixture()
def mock_history():
    history = MagicMock(spec=HistoryLog)
    now = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    history.entries_for.side_effect = lambda name: (
        [
            _entry(name, "success", now),
            _entry(name, "failure", now),
            _entry(name, "success", now),
        ]
        if name == "backup"
        else [_entry(name, "missed", now)]
    )
    return history


@pytest.fixture()
def reporter(mock_scheduler, mock_history):
    return Reporter(scheduler=mock_scheduler, history=mock_history)


class TestReporter:
    def test_generate_returns_status_report(self, reporter):
        report = reporter.generate()
        assert isinstance(report, StatusReport)

    def test_report_contains_all_jobs(self, reporter):
        report = reporter.generate()
        names = [j.job_name for j in report.jobs]
        assert "backup" in names
        assert "cleanup" in names

    def test_failed_runs_counted(self, reporter):
        report = reporter.generate()
        backup = next(j for j in report.jobs if j.job_name == "backup")
        assert backup.failed_runs == 1
        assert backup.total_runs == 3

    def test_missed_runs_counted(self, reporter):
        report = reporter.generate()
        cleanup = next(j for j in report.jobs if j.job_name == "cleanup")
        assert cleanup.missed_runs == 1

    def test_success_rate_calculation(self, reporter):
        report = reporter.generate()
        backup = next(j for j in report.jobs if j.job_name == "backup")
        assert backup.success_rate == pytest.approx(66.7)

    def test_healthy_false_when_failures(self, reporter):
        report = reporter.generate()
        assert report.healthy is False

    def test_format_text_contains_job_names(self, reporter):
        report = reporter.generate()
        text = reporter.format_text(report)
        assert "backup" in text
        assert "cleanup" in text

    def test_format_text_contains_overall_status(self, reporter):
        report = reporter.generate()
        text = reporter.format_text(report)
        assert "healthy" in text.lower()
