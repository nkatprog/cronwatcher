"""Configuration loader for cronwatcher."""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str  # cron expression, e.g. "*/5 * * * *"
    command: str
    timeout: int = 300  # seconds
    alert_on_failure: bool = True
    alert_on_missed: bool = True
    grace_period: int = 60  # seconds after expected run before alerting


@dataclass
class AlertConfig:
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None


@dataclass
class CronWatcherConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    log_file: str = "/var/log/cronwatcher.log"
    state_file: str = "/var/lib/cronwatcher/state.json"
    check_interval: int = 30  # seconds between checks


def load_config(path: str) -> CronWatcherConfig:
    """Load configuration from a JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = json.load(f)

    alert_raw = raw.get("alert", {})
    alert = AlertConfig(
        email=alert_raw.get("email"),
        webhook_url=alert_raw.get("webhook_url"),
        slack_channel=alert_raw.get("slack_channel"),
    )

    jobs = [
        JobConfig(
            name=j["name"],
            schedule=j["schedule"],
            command=j["command"],
            timeout=j.get("timeout", 300),
            alert_on_failure=j.get("alert_on_failure", True),
            alert_on_missed=j.get("alert_on_missed", True),
            grace_period=j.get("grace_period", 60),
        )
        for j in raw.get("jobs", [])
    ]

    return CronWatcherConfig(
        jobs=jobs,
        alert=alert,
        log_file=raw.get("log_file", "/var/log/cronwatcher.log"),
        state_file=raw.get("state_file", "/var/lib/cronwatcher/state.json"),
        check_interval=raw.get("check_interval", 30),
    )
