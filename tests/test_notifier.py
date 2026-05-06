"""Tests for cronwatcher.notifier."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerter import AlertEvent, Alerter
from cronwatcher.notifier import NotificationState, Notifier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_alerter() -> MagicMock:
    return MagicMock(spec=Alerter)


@pytest.fixture()
def notifier(mock_alerter: MagicMock) -> Notifier:
    return Notifier(alerter=mock_alerter, cooldown_seconds=60)


@pytest.fixture()
def sample_event() -> AlertEvent:
    return AlertEvent(job_name="backup", reason="missed", details="No heartbeat received.")


# ---------------------------------------------------------------------------
# NotificationState tests
# ---------------------------------------------------------------------------

class TestNotificationState:
    def test_should_notify_when_never_notified(self) -> None:
        state = NotificationState(job_name="job1")
        assert state.should_notify(cooldown_seconds=60) is True

    def test_should_not_notify_within_cooldown(self) -> None:
        state = NotificationState(job_name="job1")
        state.record_notification()
        assert state.should_notify(cooldown_seconds=300) is False

    def test_should_notify_after_cooldown(self) -> None:
        state = NotificationState(job_name="job1")
        state.last_notified_at = time.time() - 400
        assert state.should_notify(cooldown_seconds=300) is True

    def test_record_notification_increments_count(self) -> None:
        state = NotificationState(job_name="job1")
        state.record_notification()
        state.record_notification()
        assert state.notification_count == 2


# ---------------------------------------------------------------------------
# Notifier tests
# ---------------------------------------------------------------------------

class TestNotifier:
    def test_notify_sends_on_first_call(self, notifier: Notifier, mock_alerter: MagicMock, sample_event: AlertEvent) -> None:
        result = notifier.notify(sample_event)
        assert result is True
        mock_alerter.send.assert_called_once_with(sample_event)

    def test_notify_skips_within_cooldown(self, notifier: Notifier, mock_alerter: MagicMock, sample_event: AlertEvent) -> None:
        notifier.notify(sample_event)
        result = notifier.notify(sample_event)
        assert result is False
        mock_alerter.send.assert_called_once()  # only the first call

    def test_notify_sends_after_cooldown_elapsed(self, notifier: Notifier, mock_alerter: MagicMock, sample_event: AlertEvent) -> None:
        notifier.notify(sample_event)
        state = notifier._get_state(sample_event.job_name)
        state.last_notified_at = time.time() - 120  # past cooldown
        result = notifier.notify(sample_event)
        assert result is True
        assert mock_alerter.send.call_count == 2

    def test_notify_returns_false_on_alerter_exception(self, notifier: Notifier, mock_alerter: MagicMock, sample_event: AlertEvent) -> None:
        mock_alerter.send.side_effect = RuntimeError("SMTP down")
        result = notifier.notify(sample_event)
        assert result is False

    def test_reset_clears_state(self, notifier: Notifier, mock_alerter: MagicMock, sample_event: AlertEvent) -> None:
        notifier.notify(sample_event)
        notifier.reset(sample_event.job_name)
        # After reset, notification should go through again
        result = notifier.notify(sample_event)
        assert result is True
        assert mock_alerter.send.call_count == 2

    def test_reset_nonexistent_job_is_safe(self, notifier: Notifier) -> None:
        notifier.reset("nonexistent_job")  # should not raise
