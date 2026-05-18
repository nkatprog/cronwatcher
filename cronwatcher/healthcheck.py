"""Expose a simple HTTP health-check endpoint for cronwatcher."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import Callable

from cronwatcher.scheduler import Scheduler
from cronwatcher.reporter import Reporter


def _make_healthcheck_handler(
    scheduler: Scheduler,
    reporter: Reporter,
) -> type[BaseHTTPRequestHandler]:
    """Return a request-handler class closed over *scheduler* and *reporter*."""

    class HealthCheckHandler(BaseHTTPRequestHandler):
        """Handles GET /health requests."""

        def log_message(self, fmt: str, *args: object) -> None:  # silence access log
            pass

        def do_GET(self) -> None:
            if self.path not in ("/health", "/health/"):
                self._respond(404, {"error": "not found"})
                return

            report = reporter.build()
            payload: dict = {
                "healthy": report.healthy,
                "total_jobs": len(report.jobs),
                "failing_jobs": [
                    j.job_name for j in report.jobs if not j.healthy
                ],
            }
            status = 200 if report.healthy else 503
            self._respond(status, payload)

        def _respond(self, code: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return HealthCheckHandler
