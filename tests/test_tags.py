"""Tests for cronwatcher.tags."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from cronwatcher.tags import TagFilter, filter_jobs


# ---------------------------------------------------------------------------
# TagFilter.matches
# ---------------------------------------------------------------------------

class TestTagFilterMatches:
    def test_empty_filter_matches_everything(self):
        tf = TagFilter()
        assert tf.matches([]) is True
        assert tf.matches(["backup", "critical"]) is True

    def test_include_match(self):
        tf = TagFilter(include={"critical"})
        assert tf.matches(["critical", "db"]) is True

    def test_include_no_match(self):
        tf = TagFilter(include={"critical"})
        assert tf.matches(["backup"]) is False

    def test_exclude_blocks_job(self):
        tf = TagFilter(exclude={"disabled"})
        assert tf.matches(["disabled", "db"]) is False

    def test_exclude_allows_untagged_job(self):
        tf = TagFilter(exclude={"disabled"})
        assert tf.matches(["backup"]) is True

    def test_include_and_exclude_combined(self):
        tf = TagFilter(include={"critical"}, exclude={"disabled"})
        assert tf.matches(["critical"]) is True
        assert tf.matches(["critical", "disabled"]) is False
        assert tf.matches(["backup"]) is False


# ---------------------------------------------------------------------------
# TagFilter serialisation
# ---------------------------------------------------------------------------

class TestTagFilterSerialisation:
    def test_to_dict_roundtrip(self):
        tf = TagFilter(include={"a", "b"}, exclude={"c"})
        d = tf.to_dict()
        tf2 = TagFilter.from_dict(d)
        assert tf2.include == tf.include
        assert tf2.exclude == tf.exclude

    def test_from_dict_defaults(self):
        tf = TagFilter.from_dict({})
        assert tf.include == set()
        assert tf.exclude == set()


# ---------------------------------------------------------------------------
# filter_jobs
# ---------------------------------------------------------------------------

def _make_jobs(*tag_lists):
    return {
        f"job{i}": SimpleNamespace(tags=tags)
        for i, tags in enumerate(tag_lists)
    }


class TestFilterJobs:
    def test_no_filter_returns_all(self):
        jobs = _make_jobs(["a"], ["b"])
        result = filter_jobs(jobs, TagFilter())
        assert set(result.keys()) == {"job0", "job1"}

    def test_include_filters_correctly(self):
        jobs = _make_jobs(["critical"], ["backup"], ["critical", "db"])
        result = filter_jobs(jobs, TagFilter(include={"critical"}))
        assert set(result.keys()) == {"job0", "job2"}

    def test_exclude_filters_correctly(self):
        jobs = _make_jobs(["disabled"], ["backup"])
        result = filter_jobs(jobs, TagFilter(exclude={"disabled"}))
        assert set(result.keys()) == {"job1"}

    def test_job_without_tags_attribute(self):
        jobs = {"job0": SimpleNamespace()}
        result = filter_jobs(jobs, TagFilter())
        assert "job0" in result
