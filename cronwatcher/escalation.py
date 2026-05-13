"""Escalation policy: send alerts to additional targets after repeated failures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class EscalationRule:
    """Trigger escalation after *threshold* consecutive failures."""

    threshold: int  # number of consecutive missed/failed runs before escalating
    contacts: List[str]  # e-mail addresses or webhook URLs to notify

    @classmethod
    def from_dict(cls, data: dict) -> "EscalationRule":
        if data.get("threshold", 0) < 1:
            raise ValueError("threshold must be >= 1")
        return cls(
            threshold=int(data["threshold"]),
            contacts=list(data.get("contacts", [])),
        )

    def to_dict(self) -> dict:
        return {"threshold": self.threshold, "contacts": self.contacts}


@dataclass
class EscalationState:
    job_name: str
    consecutive_failures: int = 0
    last_escalated_at: Optional[datetime] = None
    escalated_contacts: List[str] = field(default_factory=list)

    def record_failure(self) -> None:
        self.consecutive_failures += 1

    def record_recovery(self) -> None:
        self.consecutive_failures = 0
        self.last_escalated_at = None
        self.escalated_contacts = []


class EscalationManager:
    """Decides which contacts to escalate to based on consecutive failure counts."""

    def __init__(self, rules: List[EscalationRule]) -> None:
        if not rules:
            raise ValueError("At least one escalation rule is required")
        self._rules: List[EscalationRule] = sorted(rules, key=lambda r: r.threshold)
        self._states: Dict[str, EscalationState] = {}

    def _get_state(self, job_name: str) -> EscalationState:
        if job_name not in self._states:
            self._states[job_name] = EscalationState(job_name=job_name)
        return self._states[job_name]

    def record_failure(self, job_name: str) -> None:
        self._get_state(job_name).record_failure()

    def record_recovery(self, job_name: str) -> None:
        self._get_state(job_name).record_recovery()

    def contacts_to_notify(self, job_name: str) -> List[str]:
        """Return escalation contacts that should be notified now."""
        state = self._get_state(job_name)
        contacts: List[str] = []
        for rule in self._rules:
            if state.consecutive_failures >= rule.threshold:
                for c in rule.contacts:
                    if c not in contacts:
                        contacts.append(c)
        return contacts

    def mark_escalated(self, job_name: str, contacts: List[str]) -> None:
        state = self._get_state(job_name)
        state.last_escalated_at = datetime.now(timezone.utc)
        state.escalated_contacts = list(contacts)

    def consecutive_failures(self, job_name: str) -> int:
        return self._get_state(job_name).consecutive_failures
