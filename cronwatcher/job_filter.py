"""Filter and query jobs by status, tag, or schedule pattern."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwatcher.config import JobConfig
from cronwatcher.scheduler import JobState
from cronwatcher.tags import TagFilter


@dataclass
class JobFilterCriteria:
    """Criteria used to select a subset of jobs."""

    status: Optional[str] = None          # "healthy" | "missed" | "unknown"
    tag_filter: Optional[TagFilter] = None
    name_contains: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "JobFilterCriteria":
        tag_filter = None
        if "tags" in data:
            tag_filter = TagFilter.from_dict(data["tags"])
        return cls(
            status=data.get("status"),
            tag_filter=tag_filter,
            name_contains=data.get("name_contains"),
        )


class JobFilter:
    """Applies JobFilterCriteria against a collection of jobs and their states."""

    def __init__(self, criteria: JobFilterCriteria) -> None:
        self._criteria = criteria

    def matches(self, job: JobConfig, state: Optional[JobState]) -> bool:
        c = self._criteria

        if c.name_contains and c.name_contains.lower() not in job.name.lower():
            return False

        if c.tag_filter is not None:
            tags = getattr(job, "tags", []) or []
            if not c.tag_filter.matches(tags):
                return False

        if c.status is not None:
            actual = _resolve_status(state)
            if actual != c.status:
                return False

        return True

    def apply(
        self,
        jobs: List[JobConfig],
        states: dict,  # job_name -> Optional[JobState]
    ) -> List[JobConfig]:
        """Return only jobs that satisfy all criteria."""
        return [
            job for job in jobs
            if self.matches(job, states.get(job.name))
        ]


def _resolve_status(state: Optional[JobState]) -> str:
    if state is None:
        return "unknown"
    if state.check_missed():
        return "missed"
    if state.last_heartbeat is None:
        return "unknown"
    return "healthy"
