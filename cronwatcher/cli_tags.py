"""CLI tool for listing jobs filtered by tags."""
from __future__ import annotations

import argparse
import json
import sys

from cronwatcher.config import load_config
from cronwatcher.tags import TagFilter, filter_jobs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List cron jobs filtered by tags."
    )
    parser.add_argument("config", help="Path to cronwatcher config JSON file.")
    parser.add_argument(
        "--include",
        nargs="*",
        default=[],
        metavar="TAG",
        help="Only show jobs that have at least one of these tags.",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        metavar="TAG",
        help="Hide jobs that have any of these tags.",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Output as JSON.",
    )
    return parser


def main(argv=None) -> None:  # pragma: no cover
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    tag_filter = TagFilter(
        include=set(args.include),
        exclude=set(args.exclude),
    )

    matched = filter_jobs(cfg.jobs, tag_filter)

    if args.as_json:
        output = [
            {"name": name, "tags": getattr(job, "tags", [])}
            for name, job in matched.items()
        ]
        json.dump(output, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if not matched:
            print("No jobs matched the given tag filter.")
        else:
            for name, job in matched.items():
                tags = getattr(job, "tags", []) or []
                tag_str = ", ".join(sorted(tags)) if tags else "(none)"
                print(f"{name}  [{tag_str}]")


if __name__ == "__main__":  # pragma: no cover
    main()
