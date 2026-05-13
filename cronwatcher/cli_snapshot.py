"""CLI tool for inspecting cronwatcher state snapshots."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timezone

from cronwatcher.snapshot import SnapshotManager


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect the latest cronwatcher state snapshot."
    )
    parser.add_argument(
        "snapshot_file",
        help="Path to the snapshot JSON file.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--missed-only",
        action="store_true",
        help="Only show jobs that are currently missed.",
    )
    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    manager = SnapshotManager(args.snapshot_file)
    snapshot = manager.load()

    if snapshot is None:
        print(f"No snapshot found at {args.snapshot_file}", file=sys.stderr)
        return 1

    jobs = snapshot.jobs
    if args.missed_only:
        jobs = [j for j in jobs if j.missed]

    if args.format == "json":
        print(json.dumps(
            {"captured_at": snapshot.captured_at.isoformat(), "jobs": [j.to_dict() for j in jobs]},
            indent=2,
        ))
    else:
        print(f"Snapshot captured at: {snapshot.captured_at.astimezone(timezone.utc).isoformat()}")
        print(f"{'Job':<30} {'Missed':<8} {'Consecutive Misses':<20} {'Last Heartbeat'}")
        print("-" * 80)
        for j in jobs:
            lh = j.last_heartbeat.isoformat() if j.last_heartbeat else "never"
            print(f"{j.job_name:<30} {str(j.missed):<8} {j.consecutive_misses:<20} {lh}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
