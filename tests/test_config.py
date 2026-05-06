"""Tests for cronwatcher configuration loader."""

import json
import os
import pytest
import tempfile

from cronwatcher.config import load_config, CronWatcherConfig, JobConfig, AlertConfig


@pytest.fixture
def sample_config_dict():
    return {
        "log_file": "/tmp/cronwatcher.log",
        "state_file": "/tmp/cronwatcher_state.json",
        "check_interval": 60,
        "alert": {
            "email": "test@example.com",
            "webhook_url": "https://hooks.example.com/test",
        },
        "jobs": [
            {
                "name": "test-job",
                "schedule": "*/10 * * * *",
                "command": "/bin/test.sh",
                "timeout": 120,
                "alert_on_failure": True,
                "alert_on_missed": False,
                "grace_period": 45,
            }
        ],
    }


@pytest.fixture
def config_file(sample_config_dict):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_config_dict, f)
        path = f.name
    yield path
    os.unlink(path)


def test_load_config_returns_correct_type(config_file):
    config = load_config(config_file)
    assert isinstance(config, CronWatcherConfig)


def test_load_config_jobs(config_file):
    config = load_config(config_file)
    assert len(config.jobs) == 1
    job = config.jobs[0]
    assert isinstance(job, JobConfig)
    assert job.name == "test-job"
    assert job.schedule == "*/10 * * * *"
    assert job.command == "/bin/test.sh"
    assert job.timeout == 120
    assert job.alert_on_failure is True
    assert job.alert_on_missed is False
    assert job.grace_period == 45


def test_load_config_alert(config_file):
    config = load_config(config_file)
    assert isinstance(config.alert, AlertConfig)
    assert config.alert.email == "test@example.com"
    assert config.alert.webhook_url == "https://hooks.example.com/test"
    assert config.alert.slack_channel is None


def test_load_config_top_level_fields(config_file):
    config = load_config(config_file)
    assert config.log_file == "/tmp/cronwatcher.log"
    assert config.state_file == "/tmp/cronwatcher_state.json"
    assert config.check_interval == 60


def test_load_config_defaults():
    minimal = {"jobs": [{"name": "j", "schedule": "* * * * *", "command": "/bin/true"}]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(minimal, f)
        path = f.name
    try:
        config = load_config(path)
        assert config.check_interval == 30
        assert config.jobs[0].timeout == 300
        assert config.jobs[0].grace_period == 60
    finally:
        os.unlink(path)


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.json")


def test_load_config_invalid_json():
    """Ensure a ValueError (or similar) is raised when the config file contains invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{this is not valid json")
        path = f.name
    try:
        with pytest.raises((ValueError, json.JSONDecodeError)):
            load_config(path)
    finally:
        os.unlink(path)
