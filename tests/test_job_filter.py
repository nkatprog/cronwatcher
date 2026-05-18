"""Tests for cronwatcher.job_filter."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.job_filter import JobFilter, JobFilterCriteria, _resolve_status
from cronwatcher.tags import TagFilter


def _make_job(name: str, tags: list | None = None) -> JobConfig:
    job = MagicMock(spec=JobConfig)
    job.name = name
    job.tags = tags or []
    return job


def _make_state(missed: bool, has_heartbeat: bool = True):
    state = MagicMock()
    state.check_missed.return_value = missed
    state.last_heartbeat = datetime.now(timezone.utc) if has_heartbeat else None
    return state


# ---------------------------------------------------------------------------
# _resolve_status
# ---------------------------------------------------------------------------

class TestResolveStatus:
    def test_none_state_is_unknown(self):
        assert _resolve_status(None) == "unknown"

    def test_missed_state(self):
        assert _resolve_status(_make_state(missed=True)) == "missed"

    def test_healthy_state(self):
        assert _resolve_status(_make_state(missed=False)) == "healthy"

    def test_no_heartbeat_is_unknown(self):
        assert _resolve_status(_make_state(missed=False, has_heartbeat=False)) == "unknown"


# ---------------------------------------------------------------------------
# JobFilterCriteria.from_dict
# ---------------------------------------------------------------------------

class TestJobFilterCriteriaFromDict:
    def test_empty_dict(self):
        c = JobFilterCriteria.from_dict({})
        assert c.status is None
        assert c.tag_filter is None
        assert c.name_contains is None

    def test_status_field(self):
        c = JobFilterCriteria.from_dict({"status": "missed"})
        assert c.status == "missed"

    def test_tag_filter_created(self):
        c = JobFilterCriteria.from_dict({"tags": {"include": ["prod"]}})
        assert c.tag_filter is not None


# ---------------------------------------------------------------------------
# JobFilter.matches
# ---------------------------------------------------------------------------

class TestJobFilterMatches:
    def test_no_criteria_matches_everything(self):
        f = JobFilter(JobFilterCriteria())
        assert f.matches(_make_job("backup"), None) is True

    def test_name_contains_match(self):
        f = JobFilter(JobFilterCriteria(name_contains="back"))
        assert f.matches(_make_job("backup"), None) is True

    def test_name_contains_no_match(self):
        f = JobFilter(JobFilterCriteria(name_contains="sync"))
        assert f.matches(_make_job("backup"), None) is False

    def test_status_filter_missed(self):
        f = JobFilter(JobFilterCriteria(status="missed"))
        assert f.matches(_make_job("j"), _make_state(missed=True)) is True
        assert f.matches(_make_job("j"), _make_state(missed=False)) is False

    def test_tag_filter_applied(self):
        tf = TagFilter(include=["prod"], exclude=[])
        f = JobFilter(JobFilterCriteria(tag_filter=tf))
        assert f.matches(_make_job("j", tags=["prod"]), None) is True
        assert f.matches(_make_job("j", tags=["dev"]), None) is False


# ---------------------------------------------------------------------------
# JobFilter.apply
# ---------------------------------------------------------------------------

class TestJobFilterApply:
    def test_apply_filters_list(self):
        jobs = [_make_job("a"), _make_job("b"), _make_job("c")]
        states = {
            "a": _make_state(missed=True),
            "b": _make_state(missed=False),
            "c": None,
        }
        f = JobFilter(JobFilterCriteria(status="missed"))
        result = f.apply(jobs, states)
        assert len(result) == 1
        assert result[0].name == "a"
