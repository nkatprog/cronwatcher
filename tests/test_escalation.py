"""Tests for cronwatcher.escalation."""

from __future__ import annotations

import pytest

from cronwatcher.escalation import EscalationManager, EscalationRule


# ---------------------------------------------------------------------------
# EscalationRule
# ---------------------------------------------------------------------------

class TestEscalationRule:
    def test_from_dict_valid(self):
        rule = EscalationRule.from_dict({"threshold": 3, "contacts": ["ops@example.com"]})
        assert rule.threshold == 3
        assert rule.contacts == ["ops@example.com"]

    def test_from_dict_zero_threshold_raises(self):
        with pytest.raises(ValueError):
            EscalationRule.from_dict({"threshold": 0, "contacts": []})

    def test_to_dict_roundtrip(self):
        rule = EscalationRule(threshold=2, contacts=["a@b.com", "c@d.com"])
        assert EscalationRule.from_dict(rule.to_dict()) == rule


# ---------------------------------------------------------------------------
# EscalationManager
# ---------------------------------------------------------------------------

@pytest.fixture()
def manager() -> EscalationManager:
    return EscalationManager([
        EscalationRule(threshold=2, contacts=["level1@example.com"]),
        EscalationRule(threshold=4, contacts=["level2@example.com"]),
    ])


class TestEscalationManager:
    def test_no_contacts_before_threshold(self, manager):
        manager.record_failure("backup")
        assert manager.contacts_to_notify("backup") == []

    def test_contacts_at_threshold(self, manager):
        manager.record_failure("backup")
        manager.record_failure("backup")
        assert manager.contacts_to_notify("backup") == ["level1@example.com"]

    def test_higher_threshold_adds_more_contacts(self, manager):
        for _ in range(4):
            manager.record_failure("backup")
        contacts = manager.contacts_to_notify("backup")
        assert "level1@example.com" in contacts
        assert "level2@example.com" in contacts

    def test_recovery_resets_state(self, manager):
        for _ in range(4):
            manager.record_failure("backup")
        manager.record_recovery("backup")
        assert manager.contacts_to_notify("backup") == []
        assert manager.consecutive_failures("backup") == 0

    def test_independent_jobs(self, manager):
        manager.record_failure("job_a")
        manager.record_failure("job_a")
        assert manager.contacts_to_notify("job_b") == []

    def test_mark_escalated_stores_contacts(self, manager):
        for _ in range(2):
            manager.record_failure("backup")
        contacts = manager.contacts_to_notify("backup")
        manager.mark_escalated("backup", contacts)
        state = manager._get_state("backup")
        assert state.escalated_contacts == contacts
        assert state.last_escalated_at is not None

    def test_empty_rules_raises(self):
        with pytest.raises(ValueError):
            EscalationManager([])

    def test_consecutive_failures_counter(self, manager):
        for i in range(3):
            manager.record_failure("myjob")
        assert manager.consecutive_failures("myjob") == 3
