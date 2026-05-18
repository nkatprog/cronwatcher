"""Tests for cronwatcher.job_annotations."""
import json
import os
import pytest

from cronwatcher.job_annotations import AnnotationStore, JobAnnotations


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ann_file(tmp_path):
    return str(tmp_path / "annotations.json")


@pytest.fixture
def store(ann_file):
    return AnnotationStore(ann_file)


# ---------------------------------------------------------------------------
# JobAnnotations unit tests
# ---------------------------------------------------------------------------

class TestJobAnnotations:
    def test_set_and_get(self):
        ann = JobAnnotations()
        ann.set("owner", "alice")
        assert ann.get("owner") == "alice"

    def test_get_missing_returns_none(self):
        ann = JobAnnotations()
        assert ann.get("nonexistent") is None

    def test_overwrite_value(self):
        ann = JobAnnotations()
        ann.set("env", "staging")
        ann.set("env", "production")
        assert ann.get("env") == "production"

    def test_remove_existing(self):
        ann = JobAnnotations()
        ann.set("note", "temporary")
        ann.remove("note")
        assert ann.get("note") is None

    def test_remove_missing_is_noop(self):
        ann = JobAnnotations()
        ann.remove("ghost")  # should not raise

    def test_empty_key_raises(self):
        ann = JobAnnotations()
        with pytest.raises(ValueError):
            ann.set("", "value")

    def test_to_dict_roundtrip(self):
        ann = JobAnnotations()
        ann.set("team", "platform")
        ann.set("priority", "high")
        restored = JobAnnotations.from_dict(ann.to_dict())
        assert restored.all() == ann.all()

    def test_all_returns_copy(self):
        ann = JobAnnotations()
        ann.set("k", "v")
        result = ann.all()
        result["k"] = "mutated"
        assert ann.get("k") == "v"


# ---------------------------------------------------------------------------
# AnnotationStore integration tests
# ---------------------------------------------------------------------------

class TestAnnotationStore:
    def test_set_persists_to_disk(self, store, ann_file):
        store.set("job_a", "owner", "bob")
        with open(ann_file) as fh:
            data = json.load(fh)
        assert data["job_a"]["owner"] == "bob"

    def test_reload_restores_state(self, ann_file):
        s1 = AnnotationStore(ann_file)
        s1.set("job_b", "env", "prod")
        s2 = AnnotationStore(ann_file)
        assert s2.get("job_b").get("env") == "prod"

    def test_remove_persists_to_disk(self, store, ann_file):
        store.set("job_c", "tmp", "yes")
        store.remove("job_c", "tmp")
        with open(ann_file) as fh:
            data = json.load(fh)
        assert "tmp" not in data.get("job_c", {})

    def test_all_for_job_empty_when_new(self, store):
        assert store.all_for_job("unknown_job") == {}

    def test_missing_file_starts_empty(self, ann_file):
        assert not os.path.exists(ann_file)
        s = AnnotationStore(ann_file)
        assert s.all_for_job("any") == {}
