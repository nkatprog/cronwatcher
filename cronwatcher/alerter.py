"""Alerter module: sends notifications when cron jobs fail or are missed."""

import logging
import smtplib
import urllib.request
import urllib.error
import json
from email.mime.text import MIMEText
from dataclasses import dataclass
from typing import Optional

from cronwatcher.config import AlertConfig

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    job_name: str
    reason: str  # "missed" or "failure"
    details: Optional[str] = None


class Alerter:
    """Sends alerts via configured channels (email and/or webhook)."""

    def __init__(self, config: AlertConfig) -> None:
        self.config = config

    def send(self, event: AlertEvent) -> None:
        """Dispatch alert through all configured channels."""
        subject = f"[cronwatcher] {event.reason.upper()}: {event.job_name}"
        body = self._build_body(event)

        if self.config.email:
            self._send_email(subject, body)

        if self.config.webhook_url:
            self._send_webhook(event, subject, body)

    def _build_body(self, event: AlertEvent) -> str:
        lines = [
            f"Job     : {event.job_name}",
            f"Reason  : {event.reason}",
        ]
        if event.details:
            lines.append(f"Details : {event.details}")
        return "\n".join(lines)

    def _send_email(self, subject: str, body: str) -> None:
        cfg = self.config
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = cfg.email_from or "cronwatcher@localhost"
        msg["To"] = cfg.email

        try:
            with smtplib.SMTP(cfg.smtp_host or "localhost", cfg.smtp_port or 25) as smtp:
                smtp.sendmail(msg["From"], [msg["To"]], msg.as_string())
            logger.info("Email alert sent to %s for job '%s'", cfg.email, subject)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send email alert: %s", exc)

    def _send_webhook(self, event: AlertEvent, subject: str, body: str) -> None:
        payload = json.dumps({
            "subject": subject,
            "job_name": event.job_name,
            "reason": event.reason,
            "details": event.details or "",
        }).encode()

        req = urllib.request.Request(
            self.config.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
            logger.info("Webhook alert sent for job '%s'", event.job_name)
        except urllib.error.URLError as exc:
            logger.error("Failed to send webhook alert: %s", exc)
