"""CLI tool for managing silence windows.

Usage examples:
  cronwatcher-silence list
  cronwatcher-silence add --start 02:00 --end 04:00 [--job backup]
  cronwatcher-silence remove --index 0
"""

from __future__ import annotations

import argparse
import sys
from datetime import time

from cronwatcher.silence import SilenceManager, SilenceWindow

DEFAULT_PATH = "/var/lib/cronwatcher/silences.json"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher-silence",
        description="Manage cronwatcher alert silence windows.",
    )
    parser.add_argument(
        "--file",
        default=DEFAULT_PATH,
        help="Path to silence windows JSON file (default: %(default)s)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # list
    sub.add_parser("list", help="List all active silence windows")

    # add
    add_p = sub.add_parser("add", help="Add a new silence window")
    add_p.add_argument("--start", required=True, metavar="HH:MM", help="Window start time")
    add_p.add_argument("--end", required=True, metavar="HH:MM", help="Window end time")
    add_p.add_argument("--job", default=None, metavar="JOB_NAME", help="Limit to a specific job")

    # remove
    rm_p = sub.add_parser("remove", help="Remove a silence window by index")
    rm_p.add_argument("--index", required=True, type=int, help="Zero-based index from 'list'")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    manager = SilenceManager(path=args.file)

    if args.command == "list":
        if not manager.windows:
            print("No silence windows configured.")
            return 0
        for i, w in enumerate(manager.windows):
            job_label = w.job_name or "<all jobs>"
            print(f"[{i}] {w.start.strftime('%H:%M')} – {w.end.strftime('%H:%M')}  job={job_label}")
        return 0

    if args.command == "add":
        try:
            start = time.fromisoformat(args.start)
            end = time.fromisoformat(args.end)
        except ValueError as exc:
            print(f"Error: invalid time format — {exc}", file=sys.stderr)
            return 1
        window = SilenceWindow(start=start, end=end, job_name=args.job)
        manager.add(window)
        print(f"Added silence window: {window.to_dict()}")
        return 0

    if args.command == "remove":
        if args.index < 0 or args.index >= len(manager.windows):
            print(f"Error: index {args.index} out of range.", file=sys.stderr)
            return 1
        removed = manager.windows[args.index]
        manager.remove(args.index)
        print(f"Removed silence window: {removed.to_dict()}")
        return 0

    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())
