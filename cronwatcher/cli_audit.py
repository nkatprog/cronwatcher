"""CLI tool for inspecting the cronwatcher audit log."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from cronwatcher.audit import AuditLog


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher-audit",
        description="Inspect the cronwatcher audit log.",
    )
    parser.add_argument(
        "--log",
        default="audit.json",
        metavar="FILE",
        help="Path to the audit log file (default: audit.json).",
    )
    parser.add_argument(
        "--event-type",
        metavar="TYPE",
        default=None,
        help="Filter entries by event type.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Show only the last N entries.",
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    audit = AuditLog(args.log)

    entries = (
        audit.entries_for(args.event_type)
        if args.event_type
        else audit.all_entries()
    )

    if args.limit is not None:
        entries = entries[-args.limit :]

    if not entries:
        print("No audit entries found.")
        return

    if args.format == "json":
        print(json.dumps([e.to_dict() for e in entries], indent=2))
    else:
        for e in entries:
            print(
                f"[{e.timestamp.isoformat()}] "
                f"{e.event_type:<20} actor={e.actor:<10} {e.detail}"
            )


if __name__ == "__main__":  # pragma: no cover
    main()
