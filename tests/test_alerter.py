"""Tests for the Alerter module."""

import json
import smtplib
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerter import AlertEvent, Alerter
from cronwatcher.config import AlertConfig


@pytest.fixture()
def email_config() -> AlertConfig:
    return AlertConfig(
        email="ops@example.com",
        email_from="cronwatcher@example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        webhook_url=None,
    )


@pytest.fixture()
def webhook_config() -> AlertConfig:
    return AlertConfig(
        email=None,
        webhook_url="https://hooks.example.com/notify",
    )


@pytest.fixture()
def sample_event() -> AlertEvent:
    return AlertEvent(job_name="backup-db", reason="missed", details="Expected every 1h")


class TestAlerter:
    def test_send_email_called(self, email_config, sample_event):
        alerter = Alerter(email_config)
        with patch.object(alerter, "_send_email") as mock_email, \
             patch.object(alerter, "_send_webhook") as mock_webhook:
            alerter.send(sample_event)
            mock_email.assert_called_once()
            mock_webhook.assert_not_called()

    def test_send_webhook_called(self, webhook_config, sample_event):
        alerter = Alerter(webhook_config)
        with patch.object(alerter, "_send_email") as mock_email, \
             patch.object(alerter, "_send_webhook") as mock_webhook:
            alerter.send(sample_event)
            mock_webhook.assert_called_once()
            mock_email.assert_not_called()

    def test_email_subject_contains_job_name(self, email_config, sample_event):
        alerter = Alerter(email_config)
        captured = {}

        def fake_send_email(subject, body):
            captured["subject"] = subject
            captured["body"] = body

        alerter._send_email = fake_send_email
        with patch.object(alerter, "_send_webhook"):
            alerter.send(sample_event)

        assert "backup-db" in captured["subject"]
        assert "MISSED" in captured["subject"]

    def test_body_contains_details(self, email_config, sample_event):
        alerter = Alerter(email_config)
        body = alerter._build_body(sample_event)
        assert "Expected every 1h" in body
        assert "backup-db" in body

    def test_smtp_failure_logs_error(self, email_config, sample_event, caplog):
        alerter = Alerter(email_config)
        with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("conn refused")):
            import logging
            with caplog.at_level(logging.ERROR, logger="cronwatcher.alerter"):
                alerter._send_email("subject", "body")
        assert "Failed to send email alert" in caplog.text

    def test_webhook_sends_json_payload(self, webhook_config, sample_event):
        alerter = Alerter(webhook_config)
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            alerter._send_webhook(sample_event, "subject", "body")
            request_arg = mock_open.call_args[0][0]
            payload = json.loads(request_arg.data)
            assert payload["job_name"] == "backup-db"
            assert payload["reason"] == "missed"
