"""CLI tool for pruning cronwatcher history based on retention policy."""

from __future__ import annotations

import argparse
import sys

from cronwatcher.config import load_config
from cronwatcher.history import HistoryLog
from cronwatcher.retention import HistoryPruner, RetentionPolicy


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prune old cronwatcher history entries."
    )
    parser.add_argument(
        "--config", required=True, help="Path to cronwatcher config JSON file."
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=30,
        help="Maximum age in days for history entries (default: 30).",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=100,
        help="Maximum entries to retain per job (default: 100). Use 0 for unlimited.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many entries would be pruned without modifying anything.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    max_entries = args.max_entries if args.max_entries > 0 else None
    policy = RetentionPolicy(
        max_age_days=args.max_age_days,
        max_entries_per_job=max_entries,
    )
    history = HistoryLog(cfg.history_file)
    history.load()

    if args.dry_run:
        cutoff = policy.cutoff_time()
        count = sum(
            1
            for entries in history._entries.values()
            for e in entries
            if e.timestamp < cutoff
        )
        print(f"Dry run: {count} entries would be pruned.")
        sys.exit(0)

    pruner = HistoryPruner(history, policy)
    removed = pruner.prune()
    print(f"Pruned {removed} history entries.")


if __name__ == "__main__":
    main()
