"""YinyangAlertQueue — manages alerts from solaceagi.com with Anti-Clippy discipline.

Rules:
- Poll on user interaction ONLY (never background polling)
- Surface in bottom rail on next chat message
- Never interrupt, never auto-expand for low-priority
- High-priority alerts surface first

Anti-Clippy: Alerts are passive. They wait to be asked. They never interrupt.
Fallback Ban: No silent failures. Specific exceptions only.

Channel [7] — Context + Tools.  Rung: 65537.
DNA: alerts(push | poll | dismiss) → priority_queue → display(highest_first) → Anti-Clippy
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("solace-browser.yinyang.alert_queue")

# Default storage location
_DEFAULT_SOLACE_HOME = Path("~/.solace").expanduser()

# Valid alert types
VALID_ALERT_TYPES = frozenset({
    "app_update",
    "support_reply",
    "usage_warning",
    "new_app",
    "system",
    "celebration",
})

# Priority ordering (highest priority first)
# system > usage_warning > support_reply > app_update > celebration > new_app
PRIORITY_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

# Alert type default priority (used for display ordering within same priority)
ALERT_TYPE_PRIORITY: dict[str, int] = {
    "system": 0,
    "usage_warning": 1,
    "support_reply": 2,
    "app_update": 3,
    "celebration": 4,
    "new_app": 5,
}

# Valid priority levels
VALID_PRIORITIES = frozenset({"critical", "high", "medium", "low"})


class InvalidAlertTypeError(Exception):
    """Raised when an invalid alert type is used."""


class InvalidPriorityError(Exception):
    """Raised when an invalid priority level is used."""


class AlertNotFoundError(Exception):
    """Raised when an alert_id is not found."""


class YinyangAlertQueue:
    """Manages alerts from solaceagi.com.

    Rules:
    - Poll on user interaction ONLY (never background polling)
    - Surface in bottom rail on next chat message
    - Never interrupt, never auto-expand for low-priority
    - High-priority alerts surface first
    """

    def __init__(
        self,
        solace_home: Path | None = None,
        api_base_url: str = "https://solaceagi.com",
    ) -> None:
        self._solace_home = Path(solace_home) if solace_home is not None else _DEFAULT_SOLACE_HOME
        self._api_base_url = api_base_url.rstrip("/")
        self._queue_file = self._solace_home / "alerts" / "queue.json"

    def poll_pending(self) -> list[dict[str, Any]]:
        """Fetch pending alerts from local queue file.

        Returns list of alert dicts sorted by priority (highest first),
        then by alert type priority, then by creation time (oldest first).

        Returns:
            [{alert_id, type, priority, message, created_at, auto_expand}]
        """
        alerts = self._load_queue()
        pending = [a for a in alerts if a.get("status") == "pending"]
        pending.sort(key=self._sort_key)
        return pending

    def push_local(
        self,
        alert_type: str,
        message: str,
        priority: str = "low",
    ) -> dict[str, Any]:
        """Push a local alert (for testing / offline mode).

        Args:
            alert_type: One of app_update, support_reply, usage_warning,
                        new_app, system, celebration.
            message: The alert message text.
            priority: One of critical, high, medium, low.

        Returns:
            {alert_id: str, type: str, priority: str, message: str,
             created_at: str, status: str, auto_expand: bool}
        """
        if alert_type not in VALID_ALERT_TYPES:
            raise InvalidAlertTypeError(
                f"Invalid alert type '{alert_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_ALERT_TYPES))}"
            )
        if priority not in VALID_PRIORITIES:
            raise InvalidPriorityError(
                f"Invalid priority '{priority}'. "
                f"Must be one of: {', '.join(sorted(VALID_PRIORITIES))}"
            )
        if not message or not message.strip():
            raise ValueError("message must not be empty")

        alert_id = f"alert-{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()

        # Anti-Clippy: only auto-expand for critical/high priority
        auto_expand = priority in ("critical", "high")

        alert = {
            "alert_id": alert_id,
            "type": alert_type,
            "priority": priority,
            "message": message.strip(),
            "created_at": created_at,
            "status": "pending",
            "auto_expand": auto_expand,
        }

        alerts = self._load_queue()
        alerts.append(alert)
        self._save_queue(alerts)

        logger.info(
            "Pushed local alert %s (type=%s, priority=%s)",
            alert_id, alert_type, priority,
        )

        return alert

    def dismiss(self, alert_id: str) -> dict[str, Any]:
        """Dismiss a specific alert by ID.

        Returns:
            {alert_id: str, status: "dismissed"}
        """
        if not alert_id or not alert_id.strip():
            raise ValueError("alert_id must not be empty")

        alerts = self._load_queue()
        found = False
        for alert in alerts:
            if alert.get("alert_id") == alert_id:
                alert["status"] = "dismissed"
                alert["dismissed_at"] = datetime.now(timezone.utc).isoformat()
                found = True
                break

        if not found:
            raise AlertNotFoundError(f"Alert not found: {alert_id}")

        self._save_queue(alerts)
        logger.info("Dismissed alert %s", alert_id)

        return {"alert_id": alert_id, "status": "dismissed"}

    def dismiss_all(self) -> dict[str, Any]:
        """Dismiss all pending alerts.

        Returns:
            {dismissed_count: int, status: "all_dismissed"}
        """
        alerts = self._load_queue()
        dismissed_count = 0
        now = datetime.now(timezone.utc).isoformat()

        for alert in alerts:
            if alert.get("status") == "pending":
                alert["status"] = "dismissed"
                alert["dismissed_at"] = now
                dismissed_count += 1

        self._save_queue(alerts)
        logger.info("Dismissed %d alerts", dismissed_count)

        return {"dismissed_count": dismissed_count, "status": "all_dismissed"}

    def get_next_for_display(self) -> dict[str, Any] | None:
        """Get the highest-priority undismissed alert for display.

        Priority order: system > usage_warning > support_reply > app_update > celebration > new_app
        Within same priority level, oldest alert first.

        Returns alert dict or None if no pending alerts.
        """
        pending = self.poll_pending()
        if not pending:
            return None
        return pending[0]

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _load_queue(self) -> list[dict[str, Any]]:
        """Load the alert queue from disk."""
        if not self._queue_file.exists():
            return []

        raw = json.loads(self._queue_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return []

        alerts = raw.get("alerts", [])
        if not isinstance(alerts, list):
            return []

        return alerts

    def _save_queue(self, alerts: list[dict[str, Any]]) -> None:
        """Save the alert queue to disk."""
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"alerts": alerts}
        self._queue_file.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _sort_key(alert: dict[str, Any]) -> tuple[int, int, str]:
        """Sort key for alerts: priority (asc), type priority (asc), created_at (asc).

        Lower numbers = higher priority = surfaces first.
        """
        priority_rank = PRIORITY_ORDER.get(alert.get("priority", "low"), 3)
        type_rank = ALERT_TYPE_PRIORITY.get(alert.get("type", "new_app"), 5)
        created_at = alert.get("created_at", "")
        return (priority_rank, type_rank, created_at)
