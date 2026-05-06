"""Tests for cronwatcher.report_sender."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.report_sender import ReportSender
from cronwatcher.reporter import StatusReport


@pytest.fixture()
def mock_reporter():
    reporter = MagicMock()
    report = MagicMock(spec=StatusReport)
    report.generated_at = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    reporter.generate.return_value = report
    reporter.format_text.return_value = "Report text"
    return reporter


@pytest.fixture()
def mock_alerter():
    return MagicMock()


@pytest.fixture()
def sender(mock_reporter, mock_alerter):
    return ReportSender(reporter=mock_reporter, alerter=mock_alerter, interval_seconds=3600)


class TestReportSender:
    def test_due_when_never_sent(self, sender):
        assert sender.due() is True

    def test_not_due_immediately_after_send(self, sender):
        now = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        sender.send_if_due(now=now)
        assert sender.due(now=now) is False

    def test_due_after_interval(self, sender):
        t0 = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        sender.send_if_due(now=t0)
        later = t0 + timedelta(hours=1)
        assert sender.due(now=later) is True

    def test_send_if_due_returns_true_when_sent(self, sender):
        result = sender.send_if_due()
        assert result is True

    def test_send_if_due_returns_false_when_not_due(self, sender):
        now = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        sender.send_if_due(now=now)
        result = sender.send_if_due(now=now)
        assert result is False

    def test_alerter_send_called_on_dispatch(self, sender, mock_alerter):
        sender.send_if_due()
        mock_alerter.send.assert_called_once()

    def test_alert_event_kind_is_report(self, sender, mock_alerter):
        sender.send_if_due()
        event = mock_alerter.send.call_args[0][0]
        assert event.kind == "report"

    def test_last_sent_updated(self, sender):
        now = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        sender.send_if_due(now=now)
        assert sender._last_sent == now
