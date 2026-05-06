"""CLI entry point: print a one-shot status report to stdout."""

import argparse
import json
import sys
from datetime import timezone

from cronwatcher.config import load_config
from cronwatcher.history import HistoryLog
from cronwatcher.scheduler import Scheduler
from cronwatcher.reporter import Reporter


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher-report",
        description="Print a status report for all monitored cron jobs.",
    )
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading config: {exc}", file=sys.stderr)
        return 1

    history = HistoryLog(config.history_path)
    scheduler = Scheduler(config.jobs)
    reporter = Reporter(scheduler=scheduler, history=history)
    report = reporter.generate()

    if args.format == "json":
        data = {
            "generated_at": report.generated_at.isoformat(),
            "healthy": report.healthy,
            "jobs": [
                {
                    "job_name": j.job_name,
                    "total_runs": j.total_runs,
                    "failed_runs": j.failed_runs,
                    "missed_runs": j.missed_runs,
                    "success_rate": j.success_rate,
                    "last_seen": j.last_seen.isoformat() if j.last_seen else None,
                }
                for j in report.jobs
            ],
        }
        print(json.dumps(data, indent=2))
    else:
        print(reporter.format_text(report))

    return 0 if report.healthy else 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
