"""Tests for cronwatcher.metrics_api HTTP handler."""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.metrics import MetricsCollector
from cronwatcher.metrics_api import MetricsAPIHandler


def _make_handler(collector: MetricsCollector, path: str = "/metrics"):
    HandlerClass = MetricsAPIHandler(collector)
    handler = HandlerClass.__new__(HandlerClass)
    handler.path = path
    handler.wfile = BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


@pytest.fixture
def collector():
    c = MetricsCollector()
    c.record_ping("daily_backup")
    c.record_missed("daily_backup")
    return c


class TestMetricsAPIHandler:
    def test_get_metrics_returns_200(self, collector):
        handler = _make_handler(collector)
        handler.do_GET()
        handler.send_response.assert_called_once_with(200)

    def test_get_metrics_returns_json_list(self, collector):
        handler = _make_handler(collector)
        handler.do_GET()
        handler.wfile.seek(0)
        body = json.loads(handler.wfile.read())
        assert isinstance(body, list)
        assert body[0]["job_name"] == "daily_backup"

    def test_get_metrics_counts_correct(self, collector):
        handler = _make_handler(collector)
        handler.do_GET()
        handler.wfile.seek(0)
        body = json.loads(handler.wfile.read())
        assert body[0]["total_pings"] == 1
        assert body[0]["total_missed"] == 1

    def test_unknown_path_returns_404(self, collector):
        handler = _make_handler(collector, path="/unknown")
        handler.do_GET()
        handler.send_response.assert_called_once_with(404)

    def test_unknown_path_returns_error_body(self, collector):
        handler = _make_handler(collector, path="/unknown")
        handler.do_GET()
        handler.wfile.seek(0)
        body = json.loads(handler.wfile.read())
        assert "error" in body
