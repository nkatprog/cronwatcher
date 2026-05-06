"""Minimal HTTP API for receiving heartbeat pings.

Exposes a single POST /heartbeat/<job_name> endpoint so cron jobs
can signal successful completion over HTTP.
"""

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from cronwatcher.heartbeat import HeartbeatReceiver

logger = logging.getLogger(__name__)

_receiver: Optional[HeartbeatReceiver] = None


def _make_handler(receiver: HeartbeatReceiver):
    class HeartbeatHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # suppress default access log
            logger.debug(fmt, *args)

        def do_POST(self):
            if not self.path.startswith("/heartbeat/"):
                self._respond(404, {"error": "Not found"})
                return

            job_name = self.path[len("/heartbeat/"):].strip("/")
            if not job_name:
                self._respond(400, {"error": "Missing job name"})
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            try:
                metadata = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._respond(400, {"error": "Invalid JSON body"})
                return

            try:
                record = receiver.ping(job_name, metadata)
                self._respond(200, {"status": "ok", "received_at": record.received_at})
            except ValueError as exc:
                self._respond(404, {"error": str(exc)})

        def _respond(self, status: int, payload: dict):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return HeartbeatHandler


def run_server(receiver: HeartbeatReceiver, host: str = "0.0.0.0", port: int = 8765) -> None:
    """Start the blocking HTTP server."""
    handler = _make_handler(receiver)
    server = HTTPServer((host, port), handler)
    logger.info("Heartbeat API listening on %s:%d", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Heartbeat API stopped.")
    finally:
        server.server_close()
