"""Thin wrapper that starts the health-check HTTP server in a daemon thread."""

from __future__ import annotations

import logging
import threading
from http.server import HTTPServer

from cronwatcher.healthcheck import _make_healthcheck_handler
from cronwatcher.scheduler import Scheduler
from cronwatcher.reporter import Reporter

log = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class HealthCheckServer:
    """Manages the lifecycle of the health-check HTTP server."""

    def __init__(
        self,
        scheduler: Scheduler,
        reporter: Reporter,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._host = host
        self._port = port
        handler_cls = _make_healthcheck_handler(scheduler, reporter)
        self._server = HTTPServer((host, port), handler_cls)
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start serving in a background daemon thread."""
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="healthcheck-server",
            daemon=True,
        )
        self._thread.start()
        log.info("Health-check server listening on %s:%s", self._host, self._port)

    def stop(self) -> None:
        """Shut down the server gracefully."""
        self._server.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=5)
        log.info("Health-check server stopped")
