"""Tests for cronwatcher.job_label."""
import pytest

from cronwatcher.job_label import JobLabels, LabelRegistry


# ---------------------------------------------------------------------------
# JobLabels unit tests
# ---------------------------------------------------------------------------

class TestJobLabels:
    def test_set_and_get(self):
        jl = JobLabels(job_name="backup")
        jl.set("env", "prod")
        assert jl.get("env") == "prod"

    def test_get_missing_returns_none(self):
        jl = JobLabels(job_name="backup")
        assert jl.get("missing") is None

    def test_overwrite_label(self):
        jl = JobLabels(job_name="backup")
        jl.set("env", "staging")
        jl.set("env", "prod")
        assert jl.get("env") == "prod"

    def test_remove_existing_label(self):
        jl = JobLabels(job_name="backup")
        jl.set("env", "prod")
        jl.remove("env")
        assert jl.get("env") is None

    def test_remove_missing_label_is_silent(self):
        jl = JobLabels(job_name="backup")
        jl.remove("nonexistent")  # should not raise

    def test_empty_key_raises(self):
        jl = JobLabels(job_name="backup")
        with pytest.raises(ValueError):
            jl.set("", "value")

    def test_to_dict_roundtrip(self):
        jl = JobLabels(job_name="sync", labels={"team": "ops", "tier": "1"})
        restored = JobLabels.from_dict(jl.to_dict())
        assert restored.job_name == jl.job_name
        assert restored.labels == jl.labels

    def test_from_dict_missing_labels_defaults_empty(self):
        jl = JobLabels.from_dict({"job_name": "nightly"})
        assert jl.labels == {}


# ---------------------------------------------------------------------------
# LabelRegistry unit tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> LabelRegistry:
    return LabelRegistry()


class TestLabelRegistry:
    def test_set_and_retrieve(self, registry: LabelRegistry):
        registry.set_label("job_a", "owner", "alice")
        assert registry.get_label("job_a", "owner") == "alice"

    def test_get_unknown_job_returns_none(self, registry: LabelRegistry):
        assert registry.get_label("ghost", "key") is None

    def test_remove_label(self, registry: LabelRegistry):
        registry.set_label("job_a", "env", "prod")
        registry.remove_label("job_a", "env")
        assert registry.get_label("job_a", "env") is None

    def test_remove_label_unknown_job_is_silent(self, registry: LabelRegistry):
        registry.remove_label("ghost", "key")  # should not raise

    def test_labels_for_returns_copy(self, registry: LabelRegistry):
        registry.set_label("job_a", "env", "dev")
        labels = registry.labels_for("job_a")
        labels["env"] = "mutated"
        assert registry.get_label("job_a", "env") == "dev"

    def test_labels_for_unknown_job_returns_empty(self, registry: LabelRegistry):
        assert registry.labels_for("ghost") == {}

    def test_find_by_label(self, registry: LabelRegistry):
        registry.set_label("job_a", "env", "prod")
        registry.set_label("job_b", "env", "staging")
        registry.set_label("job_c", "env", "prod")
        result = registry.find_by_label("env", "prod")
        assert sorted(result) == ["job_a", "job_c"]

    def test_find_by_label_no_match(self, registry: LabelRegistry):
        registry.set_label("job_a", "env", "dev")
        assert registry.find_by_label("env", "prod") == []

    def test_all_returns_all_entries(self, registry: LabelRegistry):
        registry.set_label("job_a", "k", "v")
        registry.set_label("job_b", "k", "v")
        names = {jl.job_name for jl in registry.all()}
        assert names == {"job_a", "job_b"}
