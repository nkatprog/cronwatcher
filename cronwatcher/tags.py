"""Tag-based filtering for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class TagFilter:
    """Matches jobs by tag membership."""

    include: Set[str] = field(default_factory=set)
    exclude: Set[str] = field(default_factory=set)

    def matches(self, job_tags: List[str]) -> bool:
        """Return True if *job_tags* satisfies include/exclude rules.

        - If *include* is non-empty, the job must have at least one matching tag.
        - If *exclude* is non-empty, the job must have none of those tags.
        """
        tag_set = set(job_tags)
        if self.include and not (self.include & tag_set):
            return False
        if self.exclude and (self.exclude & tag_set):
            return False
        return True

    @classmethod
    def from_dict(cls, data: dict) -> "TagFilter":
        return cls(
            include=set(data.get("include", [])),
            exclude=set(data.get("exclude", [])),
        )

    def to_dict(self) -> dict:
        return {
            "include": sorted(self.include),
            "exclude": sorted(self.exclude),
        }


def filter_jobs(job_map: dict, tag_filter: TagFilter) -> dict:
    """Return a subset of *job_map* whose jobs satisfy *tag_filter*.

    *job_map* is expected to be a mapping of job_name -> JobConfig (or any
    object that exposes a ``tags`` attribute / key).
    """
    result = {}
    for name, job in job_map.items():
        tags = getattr(job, "tags", None) or []
        if tag_filter.matches(tags):
            result[name] = job
    return result
