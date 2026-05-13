"""Tests for cronwatcher.dependency."""
import pytest
from cronwatcher.dependency import DependencyGraph, DependencyViolation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def graph() -> DependencyGraph:
    return DependencyGraph(
        deps={
            "job_b": ["job_a"],
            "job_c": ["job_a", "job_b"],
        }
    )


# ---------------------------------------------------------------------------
# DependencyGraph.dependencies_of
# ---------------------------------------------------------------------------

class TestDependenciesOf:
    def test_returns_empty_for_unknown_job(self, graph):
        assert graph.dependencies_of("nonexistent") == []

    def test_returns_single_dependency(self, graph):
        assert graph.dependencies_of("job_b") == ["job_a"]

    def test_returns_multiple_dependencies(self, graph):
        assert set(graph.dependencies_of("job_c")) == {"job_a", "job_b"}


# ---------------------------------------------------------------------------
# DependencyGraph.check
# ---------------------------------------------------------------------------

class TestCheck:
    def test_no_violation_when_no_deps(self, graph):
        assert graph.check("job_a", healthy_jobs=set()) is None

    def test_no_violation_when_all_deps_healthy(self, graph):
        assert graph.check("job_b", healthy_jobs={"job_a"}) is None

    def test_violation_when_dep_unhealthy(self, graph):
        violation = graph.check("job_b", healthy_jobs=set())
        assert isinstance(violation, DependencyViolation)
        assert violation.job_name == "job_b"
        assert "job_a" in violation.blocked_by

    def test_partial_violation_lists_only_unhealthy(self, graph):
        violation = graph.check("job_c", healthy_jobs={"job_a"})
        assert violation is not None
        assert "job_b" in violation.blocked_by
        assert "job_a" not in violation.blocked_by

    def test_violation_str_contains_job_name(self, graph):
        violation = graph.check("job_b", healthy_jobs=set())
        assert "job_b" in str(violation)
        assert "job_a" in str(violation)


# ---------------------------------------------------------------------------
# DependencyGraph.all_clear
# ---------------------------------------------------------------------------

class TestAllClear:
    def test_true_when_no_deps(self, graph):
        assert graph.all_clear("job_a", healthy_jobs=set()) is True

    def test_true_when_deps_satisfied(self, graph):
        assert graph.all_clear("job_b", healthy_jobs={"job_a"}) is True

    def test_false_when_dep_missing(self, graph):
        assert graph.all_clear("job_b", healthy_jobs=set()) is False


# ---------------------------------------------------------------------------
# DependencyGraph.from_job_configs
# ---------------------------------------------------------------------------

class TestFromJobConfigs:
    def test_builds_graph_from_configs(self):
        class FakeJob:
            def __init__(self, name, depends_on=None):
                self.name = name
                self.depends_on = depends_on

        jobs = [
            FakeJob("alpha"),
            FakeJob("beta", depends_on=["alpha"]),
        ]
        g = DependencyGraph.from_job_configs(jobs)
        assert g.dependencies_of("beta") == ["alpha"]
        assert g.dependencies_of("alpha") == []

    def test_empty_list_gives_empty_graph(self):
        g = DependencyGraph.from_job_configs([])
        assert g.dependencies_of("anything") == []
