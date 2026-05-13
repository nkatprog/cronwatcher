"""Tests for cronwatcher.escalation_hook."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from cronwatcher.escalation import EscalationManager, EscalationRule
from cronwatcher.escalation_hook import EscalationHook


@pytest.fixture()
def manager() -> EscalationManager:
    return EscalationManager([
        EscalationRule(threshold=2, contacts=["oncall@example.com"]),
        EscalationRule(threshold=3, contacts=["manager@example.com"]),
    ])


@pytest.fixture()
def mock_alerter():
    alerter = MagicMock()
    alerter.send = MagicMock()
    return alerter


@pytest.fixture()
def hook(manager, mock_alerter) -> EscalationHook:
    return EscalationHook(manager=manager, alerter=mock_alerter)


class TestEscalationHook:
    def test_no_alert_below_threshold(self, hook, mock_alerter):
        result = hook.on_missed("nightly_backup")
        assert result == []
        mock_alerter.send.assert_not_called()

    def test_alert_sent_at_threshold(self, hook, mock_alerter):
        hook.on_missed("nightly_backup")  # 1st failure — no alert
        result = hook.on_missed("nightly_backup")  # 2nd failure — escalate
        assert "oncall@example.com" in result
        assert mock_alerter.send.call_count == 1
        _, kwargs = mock_alerter.send.call_args
        assert kwargs["override_target"] == "oncall@example.com"

    def test_alert_sent_to_multiple_contacts_above_higher_threshold(self, hook, mock_alerter):
        hook.on_missed("nightly_backup")
        hook.on_missed("nightly_backup")
        mock_alerter.send.reset_mock()
        result = hook.on_missed("nightly_backup")  # 3rd failure
        assert "oncall@example.com" in result
        assert "manager@example.com" in result
        assert mock_alerter.send.call_count == 2

    def test_recovery_resets_and_no_alert(self, hook, mock_alerter):
        hook.on_missed("nightly_backup")
        hook.on_missed("nightly_backup")
        mock_alerter.send.reset_mock()
        hook.on_healthy("nightly_backup")
        result = hook.on_missed("nightly_backup")  # 1st failure after recovery
        assert result == []
        mock_alerter.send.assert_not_called()

    def test_alert_event_message_contains_job_name(self, hook, mock_alerter):
        hook.on_missed("db_dump")
        hook.on_missed("db_dump")
        event_arg = mock_alerter.send.call_args[0][0]
        assert "db_dump" in event_arg.message

    def test_independent_jobs_do_not_interfere(self, hook, mock_alerter):
        hook.on_missed("job_a")
        hook.on_missed("job_a")  # escalates job_a
        mock_alerter.send.reset_mock()
        result = hook.on_missed("job_b")  # job_b only 1 failure
        assert result == []
        mock_alerter.send.assert_not_called()
