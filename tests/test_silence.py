"""Tests for cronwatcher.silence."""

import json
import os
from datetime import datetime, time

import pytest

from cronwatcher.silence import SilenceManager, SilenceWindow


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def silence_file(tmp_path):
    return str(tmp_path / "silences.json")


@pytest.fixture
def manager(silence_file):
    return SilenceManager(path=silence_file)


# ---------------------------------------------------------------------------
# SilenceWindow
# ---------------------------------------------------------------------------


class TestSilenceWindow:
    def test_active_within_window(self):
        w = SilenceWindow(start=time(2, 0), end=time(4, 0))
        assert w.is_active(at=datetime(2024, 1, 1, 3, 0))

    def test_inactive_outside_window(self):
        w = SilenceWindow(start=time(2, 0), end=time(4, 0))
        assert not w.is_active(at=datetime(2024, 1, 1, 5, 0))

    def test_overnight_window_before_midnight(self):
        w = SilenceWindow(start=time(23, 0), end=time(1, 0))
        assert w.is_active(at=datetime(2024, 1, 1, 23, 30))

    def test_overnight_window_after_midnight(self):
        w = SilenceWindow(start=time(23, 0), end=time(1, 0))
        assert w.is_active(at=datetime(2024, 1, 2, 0, 30))

    def test_overnight_window_outside(self):
        w = SilenceWindow(start=time(23, 0), end=time(1, 0))
        assert not w.is_active(at=datetime(2024, 1, 1, 12, 0))

    def test_roundtrip_dict(self):
        w = SilenceWindow(start=time(2, 0), end=time(4, 0), job_name="backup")
        assert SilenceWindow.from_dict(w.to_dict()) == w


# ---------------------------------------------------------------------------
# SilenceManager
# ---------------------------------------------------------------------------


class TestSilenceManager:
    def test_add_persists(self, manager, silence_file):
        w = SilenceWindow(start=time(2, 0), end=time(3, 0))
        manager.add(w)
        with open(silence_file) as fh:
            data = json.load(fh)
        assert len(data) == 1
        assert data[0]["start"] == "02:00"

    def test_load_from_existing_file(self, silence_file):
        w = SilenceWindow(start=time(2, 0), end=time(3, 0), job_name="myjob")
        m1 = SilenceManager(path=silence_file)
        m1.add(w)
        m2 = SilenceManager(path=silence_file)
        assert len(m2.windows) == 1
        assert m2.windows[0].job_name == "myjob"

    def test_remove(self, manager):
        manager.add(SilenceWindow(start=time(1, 0), end=time(2, 0)))
        manager.add(SilenceWindow(start=time(3, 0), end=time(4, 0)))
        manager.remove(0)
        assert len(manager.windows) == 1
        assert manager.windows[0].start == time(3, 0)

    def test_is_silenced_global_window(self, manager):
        manager.add(SilenceWindow(start=time(2, 0), end=time(4, 0)))
        assert manager.is_silenced("any_job", at=datetime(2024, 1, 1, 3, 0))

    def test_is_silenced_specific_job(self, manager):
        manager.add(SilenceWindow(start=time(2, 0), end=time(4, 0), job_name="backup"))
        assert manager.is_silenced("backup", at=datetime(2024, 1, 1, 3, 0))
        assert not manager.is_silenced("other_job", at=datetime(2024, 1, 1, 3, 0))

    def test_not_silenced_outside_window(self, manager):
        manager.add(SilenceWindow(start=time(2, 0), end=time(4, 0)))
        assert not manager.is_silenced("any_job", at=datetime(2024, 1, 1, 5, 0))

    def test_empty_manager_not_silenced(self, manager):
        assert not manager.is_silenced("any_job")
