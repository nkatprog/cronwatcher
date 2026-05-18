"""Tests for cronwatcher.healthcheck_server."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.healthcheck_server import HealthCheckServer


@pytest.fixture()
def mock_scheduler():
    return MagicMock()


@pytest.fixture()
def mock_reporter():
    return MagicMock()


class TestHealthCheckServer:
    @patch("cronwatcher.healthcheck_server.HTTPServer")
    def test_start_spawns_daemon_thread(self, mock_httpserver, mock_scheduler, mock_reporter):
        server = HealthCheckServer(mock_scheduler, mock_reporter, port=19999)
        server.start()
        assert server._thread is not None
        assert server._thread.daemon is True
        server.stop()

    @patch("cronwatcher.healthcheck_server.HTTPServer")
    def test_stop_calls_shutdown(self, mock_httpserver, mock_scheduler, mock_reporter):
        server = HealthCheckServer(mock_scheduler, mock_reporter, port=19998)
        server.start()
        server.stop()
        server._server.shutdown.assert_called_once()

    @patch("cronwatcher.healthcheck_server.HTTPServer")
    def test_custom_host_and_port_passed_to_httpserver(
        self, mock_httpserver, mock_scheduler, mock_reporter
    ):
        HealthCheckServer(mock_scheduler, mock_reporter, host="0.0.0.0", port=9090)
        mock_httpserver.assert_called_once()
        args = mock_httpserver.call_args[0]
        assert args[0] == ("0.0.0.0", 9090)
