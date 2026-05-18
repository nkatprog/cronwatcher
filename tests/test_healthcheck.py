"""Unit tests for cronwatcher.healthcheck."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock

import pytest

from cronwatcher.healthcheck import _make_healthcheck_handler
from cronwatcher.reporter import JobReport, StatusReport


def _make_report(healthy: bool, job_names: list[str] | None = None) -> StatusReport:
    jobs = [
        JobReport(job_name=n, healthy=healthy, last_heartbeat=None, missed=not healthy)
        for n in (job_names or [])
    ]
    return StatusReport(healthy=healthy, jobs=jobs)


@pytest.fixture()
def mock_scheduler():
    return MagicMock()


@pytest.fixture()
def mock_reporter():
    return MagicMock()


def _build_handler(reporter, path="/health"):
    scheduler = MagicMock()
    cls = _make_healthcheck_handler(scheduler, reporter)
    handler = cls.__new__(cls)
    handler.path = path
    handler.wfile = io.BytesIO()
    handler._headers_buffer = []
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


class TestHealthCheckHandler:
    def test_healthy_returns_200(self, mock_reporter):
        mock_reporter.build.return_value = _make_report(True, ["job_a"])
        handler = _build_handler(mock_reporter)
        handler.do_GET()
        handler.send_response.assert_called_once_with(200)

    def test_unhealthy_returns_503(self, mock_reporter):
        mock_reporter.build.return_value = _make_report(False, ["job_b"])
        handler = _build_handler(mock_reporter)
        handler.do_GET()
        handler.send_response.assert_called_once_with(503)

    def test_response_body_contains_failing_jobs(self, mock_reporter):
        mock_reporter.build.return_value = _make_report(False, ["job_x"])
        handler = _build_handler(mock_reporter)
        handler.do_GET()
        handler.wfile.seek(0)
        body = json.loads(handler.wfile.read())
        assert "job_x" in body["failing_jobs"]

    def test_unknown_path_returns_404(self, mock_reporter):
        mock_reporter.build.return_value = _make_report(True)
        handler = _build_handler(mock_reporter, path="/unknown")
        handler.do_GET()
        handler.send_response.assert_called_once_with(404)

    def test_healthy_body_has_no_failing_jobs(self, mock_reporter):
        mock_reporter.build.return_value = _make_report(True, ["job_a", "job_b"])
        handler = _build_handler(mock_reporter)
        handler.do_GET()
        handler.wfile.seek(0)
        body = json.loads(handler.wfile.read())
        assert body["failing_jobs"] == []
        assert body["total_jobs"] == 2
