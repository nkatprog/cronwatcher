"""CLI entry-point to query the cronwatcher health-check endpoint."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from cronwatcher.healthcheck_server import DEFAULT_HOST, DEFAULT_PORT


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Query the cronwatcher health-check endpoint."
    )
    p.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="Host where cronwatcher is running (default: %(default)s)",
    )
    p.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="Health-check port (default: %(default)s)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output raw JSON instead of human-readable text",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    url = f"http://{args.host}:{args.port}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            raw = resp.read()
            code = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        code = exc.code
    except OSError as exc:
        print(f"ERROR: could not reach {url}: {exc}", file=sys.stderr)
        return 2

    data = json.loads(raw)
    if args.as_json:
        print(json.dumps(data, indent=2))
    else:
        status = "OK" if data.get("healthy") else "FAILING"
        print(f"Status : {status}")
        print(f"Jobs   : {data.get('total_jobs', 0)} total")
        failing = data.get("failing_jobs", [])
        if failing:
            print("Failing:")
            for name in failing:
                print(f"  - {name}")

    return 0 if code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
