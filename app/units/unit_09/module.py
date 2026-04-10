"""Unit 09: Alert & Response Unit — إصدار التنبيهات وفق الأولوية وتوجيهها."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum

UNIT_09_NAME = "Alert & Response Unit"


class AlertPriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Alert:
    alert_id: str
    priority: AlertPriority
    source_unit: str
    zone_id: str
    message: str
    created_at: datetime
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None

    def acknowledge(self, by: str, at: datetime | None = None) -> None:
        self.acknowledged = True
        self.acknowledged_by = by
        self.acknowledged_at = at or datetime.now(timezone.utc).replace(tzinfo=None)

    def to_dict(self) -> dict[str, object]:
        return {
            "alert_id": self.alert_id,
            "priority": self.priority.name,
            "priority_level": int(self.priority),
            "source_unit": self.source_unit,
            "zone_id": self.zone_id,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }


class AlertResponseUnit:
    """Issues, queues, and routes prioritized safety alerts."""

    def __init__(self, auto_escalate_after_seconds: float = 120.0) -> None:
        if auto_escalate_after_seconds <= 0:
            raise ValueError("auto_escalate_after_seconds must be > 0")
        self.auto_escalate_after_seconds = auto_escalate_after_seconds
        self._queue: list[Alert] = []
        self._counter: int = 0

    def issue(
        self,
        priority: AlertPriority,
        source_unit: str,
        zone_id: str,
        message: str,
        at: datetime | None = None,
    ) -> Alert:
        self._counter += 1
        alert = Alert(
            alert_id=f"ALT-{self._counter:05d}",
            priority=priority,
            source_unit=source_unit,
            zone_id=zone_id,
            message=message,
            created_at=at or datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._queue.append(alert)
        self._queue.sort(key=lambda a: (-int(a.priority), a.created_at))
        return alert

    def pending_alerts(self) -> list[Alert]:
        return [a for a in self._queue if not a.acknowledged]

    def acknowledge(self, alert_id: str, by: str, at: datetime | None = None) -> Alert | None:
        for alert in self._queue:
            if alert.alert_id == alert_id:
                alert.acknowledge(by, at)
                return alert
        return None

    def escalate_stale(self, now: datetime | None = None) -> list[Alert]:
        """Escalate unacknowledged alerts that exceeded the escalation window."""
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)
        escalated: list[Alert] = []
        for alert in self._queue:
            if alert.acknowledged:
                continue
            age = (now - alert.created_at).total_seconds()
            if age >= self.auto_escalate_after_seconds and alert.priority < AlertPriority.CRITICAL:
                alert.priority = AlertPriority(min(int(alert.priority) + 1, int(AlertPriority.CRITICAL)))
                escalated.append(alert)
        return escalated

    def summary(self) -> dict[str, object]:
        pending = self.pending_alerts()
        by_priority: dict[str, int] = {p.name: 0 for p in AlertPriority}
        for a in pending:
            by_priority[a.priority.name] += 1
        return {
            "total_issued": len(self._queue),
            "pending": len(pending),
            "by_priority": by_priority,
        }
