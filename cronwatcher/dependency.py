"""Job dependency tracking: ensure a job only alerts if its upstream jobs are healthy."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DependencyViolation:
    job_name: str
    blocked_by: List[str]

    def __str__(self) -> str:
        blocked = ", ".join(self.blocked_by)
        return f"{self.job_name} blocked by unhealthy dependencies: {blocked}"


class DependencyGraph:
    """Holds dependency relationships between jobs."""

    def __init__(self, deps: Optional[Dict[str, List[str]]] = None) -> None:
        # deps maps job_name -> list of job names it depends on
        self._deps: Dict[str, List[str]] = deps or {}

    @classmethod
    def from_job_configs(cls, job_configs: list) -> "DependencyGraph":
        """Build a DependencyGraph from a list of JobConfig objects."""
        deps: Dict[str, List[str]] = {}
        for job in job_configs:
            depends_on = getattr(job, "depends_on", None) or []
            if depends_on:
                deps[job.name] = list(depends_on)
        return cls(deps)

    def dependencies_of(self, job_name: str) -> List[str]:
        return list(self._deps.get(job_name, []))

    def check(self, job_name: str, healthy_jobs: set) -> Optional[DependencyViolation]:
        """Return a DependencyViolation if any dependency is not healthy, else None."""
        deps = self.dependencies_of(job_name)
        if not deps:
            return None
        blocked_by = [d for d in deps if d not in healthy_jobs]
        if blocked_by:
            return DependencyViolation(job_name=job_name, blocked_by=blocked_by)
        return None

    def all_clear(self, job_name: str, healthy_jobs: set) -> bool:
        """Return True only when all dependencies of job_name are healthy."""
        return self.check(job_name, healthy_jobs) is None
