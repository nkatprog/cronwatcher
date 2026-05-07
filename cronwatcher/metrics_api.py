"""HTTP handler that serves a JSON metrics endpoint."""

import json
from http.server import BaseHTTPRequestHandler
from typing import Type

from cronwatcher.metrics import MetricsCollector


def _make_metrics_handler(collector: MetricsCollector) -> Type[BaseHTTPRequestHandler]:
    class MetricsHandler(BaseHTTPRequestHandler):
        _collector = collector

        def log_message(self, fmt: str, *args) -> None:  # suppress default logging
            pass

        def do_GET(self) -> None:
            if self.path != "/metrics":
                self._respond(404, {"error": "not found"})
                return
            payload = self._collector.summary()
            self._respond(200, payload)

        def _respond(self, status: int, body) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return MetricsHandler


MetricsAPIHandler = _make_metrics_handler
