"""Configuration loading and dataclasses for cronwatcher."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class JobConfig:
    schedule: str
    timeout: int
    grace_period: int = 60
    tags: List[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "JobConfig":
        return cls(
            schedule=data["schedule"],
            timeout=data["timeout"],
            grace_period=data.get("grace_period", 60),
            tags=data.get("tags", []),
            description=data.get("description", ""),
        )


@dataclass
class AlertConfig:
    email: Optional[dict] = None
    webhook: Optional[dict] = None

    @classmethod
    def from_dict(cls, data: dict) -> "AlertConfig":
        return cls(
            email=data.get("email"),
            webhook=data.get("webhook"),
        )


@dataclass
class CronWatcherConfig:
    jobs: Dict[str, JobConfig]
    alert: AlertConfig
    check_interval: int = 60
    notification_cooldown: int = 3600
    history_file: str = "cronwatcher_history.json"
    audit_file: str = "cronwatcher_audit.json"
    silence_file: str = "cronwatcher_silence.json"
    report_interval: int = 86400

    @classmethod
    def from_dict(cls, data: dict) -> "CronWatcherConfig":
        jobs = {
            name: JobConfig.from_dict(cfg)
            for name, cfg in data.get("jobs", {}).items()
        }
        alert = AlertConfig.from_dict(data.get("alert", {}))
        return cls(
            jobs=jobs,
            alert=alert,
            check_interval=data.get("check_interval", 60),
            notification_cooldown=data.get("notification_cooldown", 3600),
            history_file=data.get("history_file", "cronwatcher_history.json"),
            audit_file=data.get("audit_file", "cronwatcher_audit.json"),
            silence_file=data.get("silence_file", "cronwatcher_silence.json"),
            report_interval=data.get("report_interval", 86400),
        )


def load_config(path: str) -> CronWatcherConfig:
    with open(path) as fh:
        data = json.load(fh)
    return CronWatcherConfig.from_dict(data)
