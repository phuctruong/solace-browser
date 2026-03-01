"""
tests/test_alert_queue.py — YinyangAlertQueue Test Suite
SolaceBrowser B12 (original T18): Alert queue for solaceagi.com notifications

Tests (23 tests):
  TestPushLocal         (6 tests)  — push alerts, validation, types
  TestPollPending       (4 tests)  — poll returns sorted, empty queue, filtering
  TestDismiss           (4 tests)  — dismiss single, not found, empty id
  TestDismissAll        (3 tests)  — dismiss all, count, empty queue
  TestGetNextForDisplay (4 tests)  — highest priority, type ordering, empty
  TestAntiClippy        (2 tests)  — auto_expand rules, passive behavior

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_alert_queue.py -v

Rung: 274177
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from yinyang.alert_queue import (
    VALID_ALERT_TYPES,
    VALID_PRIORITIES,
    AlertNotFoundError,
    InvalidAlertTypeError,
    InvalidPriorityError,
    YinyangAlertQueue,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def solace_home(tmp_path):
    """Create a temporary solace home for alert storage."""
    home = tmp_path / "solace_home"
    home.mkdir()
    return home


@pytest.fixture
def queue(solace_home):
    """Create a YinyangAlertQueue instance with temp storage."""
    return YinyangAlertQueue(solace_home=solace_home)


# ---------------------------------------------------------------------------
# TestPushLocal — push alerts to local queue
# ---------------------------------------------------------------------------

class TestPushLocal:
    """Test push_local() for adding alerts to the queue."""

    def test_push_local_returns_alert_dict(self, queue):
        """push_local returns a well-formed alert dict."""
        result = queue.push_local("app_update", "Gmail app updated to v2.0")
        assert result["alert_id"].startswith("alert-")
        assert result["type"] == "app_update"
        assert result["priority"] == "low"
        assert result["message"] == "Gmail app updated to v2.0"
        assert result["status"] == "pending"
        assert "created_at" in result
        assert "auto_expand" in result

    def test_push_local_with_high_priority(self, queue):
        """push_local with high priority sets auto_expand=True."""
        result = queue.push_local("system", "Maintenance window in 1 hour", priority="high")
        assert result["priority"] == "high"
        assert result["auto_expand"] is True

    def test_push_local_with_critical_priority(self, queue):
        """push_local with critical priority sets auto_expand=True."""
        result = queue.push_local("usage_warning", "Token budget 90% used", priority="critical")
        assert result["priority"] == "critical"
        assert result["auto_expand"] is True

    def test_push_local_invalid_type_raises(self, queue):
        """push_local with invalid alert type raises InvalidAlertTypeError."""
        with pytest.raises(InvalidAlertTypeError, match="Invalid alert type"):
            queue.push_local("invalid_type", "Some message")

    def test_push_local_invalid_priority_raises(self, queue):
        """push_local with invalid priority raises InvalidPriorityError."""
        with pytest.raises(InvalidPriorityError, match="Invalid priority"):
            queue.push_local("system", "Test", priority="urgent")

    def test_push_local_empty_message_raises(self, queue):
        """push_local with empty message raises ValueError."""
        with pytest.raises(ValueError, match="message must not be empty"):
            queue.push_local("system", "")

    def test_push_local_all_valid_types(self, queue):
        """All valid alert types are accepted."""
        for alert_type in VALID_ALERT_TYPES:
            result = queue.push_local(alert_type, f"Test {alert_type}")
            assert result["type"] == alert_type

    def test_push_local_persists_to_disk(self, queue, solace_home):
        """Pushed alert is persisted to disk."""
        queue.push_local("app_update", "Test persistence")
        queue_file = solace_home / "alerts" / "queue.json"
        assert queue_file.exists()

        raw = json.loads(queue_file.read_text(encoding="utf-8"))
        assert len(raw["alerts"]) == 1
        assert raw["alerts"][0]["message"] == "Test persistence"


# ---------------------------------------------------------------------------
# TestPollPending — fetch pending alerts
# ---------------------------------------------------------------------------

class TestPollPending:
    """Test poll_pending() for fetching and sorting alerts."""

    def test_poll_empty_queue_returns_empty_list(self, queue):
        """Empty queue returns empty list."""
        result = queue.poll_pending()
        assert result == []

    def test_poll_returns_pending_only(self, queue):
        """poll_pending only returns alerts with status 'pending'."""
        alert = queue.push_local("app_update", "Test alert")
        queue.dismiss(alert["alert_id"])

        result = queue.poll_pending()
        assert len(result) == 0

    def test_poll_returns_all_pending(self, queue):
        """poll_pending returns all pending alerts."""
        queue.push_local("app_update", "Alert one")
        queue.push_local("system", "Alert two")
        queue.push_local("celebration", "Alert three")

        result = queue.poll_pending()
        assert len(result) == 3

    def test_poll_sorted_by_priority(self, queue):
        """poll_pending returns alerts sorted by priority (highest first)."""
        queue.push_local("celebration", "Low priority", priority="low")
        queue.push_local("system", "Critical priority", priority="critical")
        queue.push_local("app_update", "Medium priority", priority="medium")

        result = queue.poll_pending()
        assert result[0]["priority"] == "critical"
        assert result[1]["priority"] == "medium"
        assert result[2]["priority"] == "low"


# ---------------------------------------------------------------------------
# TestDismiss — dismiss single alerts
# ---------------------------------------------------------------------------

class TestDismiss:
    """Test dismiss() for removing alerts from the pending queue."""

    def test_dismiss_removes_from_pending(self, queue):
        """Dismissed alert no longer appears in poll_pending."""
        alert = queue.push_local("app_update", "Test dismiss")
        queue.dismiss(alert["alert_id"])

        pending = queue.poll_pending()
        assert len(pending) == 0

    def test_dismiss_returns_status(self, queue):
        """dismiss returns {alert_id, status: 'dismissed'}."""
        alert = queue.push_local("app_update", "Test dismiss")
        result = queue.dismiss(alert["alert_id"])
        assert result["alert_id"] == alert["alert_id"]
        assert result["status"] == "dismissed"

    def test_dismiss_nonexistent_raises(self, queue):
        """Dismissing a nonexistent alert raises AlertNotFoundError."""
        with pytest.raises(AlertNotFoundError, match="Alert not found"):
            queue.dismiss("alert-nonexistent")

    def test_dismiss_empty_id_raises(self, queue):
        """Empty alert_id raises ValueError."""
        with pytest.raises(ValueError, match="alert_id must not be empty"):
            queue.dismiss("")


# ---------------------------------------------------------------------------
# TestDismissAll — dismiss all pending alerts
# ---------------------------------------------------------------------------

class TestDismissAll:
    """Test dismiss_all() for clearing the queue."""

    def test_dismiss_all_clears_queue(self, queue):
        """dismiss_all removes all pending alerts."""
        queue.push_local("app_update", "Alert one")
        queue.push_local("system", "Alert two")
        queue.push_local("celebration", "Alert three")

        queue.dismiss_all()
        pending = queue.poll_pending()
        assert len(pending) == 0

    def test_dismiss_all_returns_count(self, queue):
        """dismiss_all returns the count of dismissed alerts."""
        queue.push_local("app_update", "Alert one")
        queue.push_local("system", "Alert two")

        result = queue.dismiss_all()
        assert result["dismissed_count"] == 2
        assert result["status"] == "all_dismissed"

    def test_dismiss_all_empty_queue_returns_zero(self, queue):
        """dismiss_all on empty queue returns count 0."""
        result = queue.dismiss_all()
        assert result["dismissed_count"] == 0
        assert result["status"] == "all_dismissed"


# ---------------------------------------------------------------------------
# TestGetNextForDisplay — highest priority alert selection
# ---------------------------------------------------------------------------

class TestGetNextForDisplay:
    """Test get_next_for_display() for priority-based alert selection."""

    def test_returns_none_for_empty_queue(self, queue):
        """Empty queue returns None."""
        result = queue.get_next_for_display()
        assert result is None

    def test_returns_highest_priority_alert(self, queue):
        """Returns the highest-priority alert."""
        queue.push_local("celebration", "Party time", priority="low")
        queue.push_local("system", "System maintenance", priority="critical")
        queue.push_local("app_update", "App updated", priority="medium")

        result = queue.get_next_for_display()
        assert result is not None
        assert result["priority"] == "critical"
        assert result["message"] == "System maintenance"

    def test_same_priority_uses_type_ordering(self, queue):
        """Within same priority, system type surfaces before app_update."""
        queue.push_local("app_update", "App updated", priority="high")
        queue.push_local("system", "System alert", priority="high")

        result = queue.get_next_for_display()
        assert result is not None
        assert result["type"] == "system"

    def test_returns_none_after_all_dismissed(self, queue):
        """Returns None after all alerts are dismissed."""
        queue.push_local("app_update", "Test")
        queue.dismiss_all()

        result = queue.get_next_for_display()
        assert result is None

    def test_type_priority_order_complete(self, queue):
        """Full type priority order: system > usage_warning > support_reply > app_update > celebration > new_app."""
        # Push in reverse priority order
        queue.push_local("new_app", "New app available", priority="high")
        queue.push_local("celebration", "Achievement unlocked", priority="high")
        queue.push_local("app_update", "Gmail updated", priority="high")
        queue.push_local("support_reply", "Support replied", priority="high")
        queue.push_local("usage_warning", "Budget warning", priority="high")
        queue.push_local("system", "System update", priority="high")

        # Get all in order
        types_in_order = []
        for _ in range(6):
            alert = queue.get_next_for_display()
            assert alert is not None
            types_in_order.append(alert["type"])
            queue.dismiss(alert["alert_id"])

        assert types_in_order == [
            "system", "usage_warning", "support_reply",
            "app_update", "celebration", "new_app",
        ]


# ---------------------------------------------------------------------------
# TestAntiClippy — alerts are passive, never interrupt
# ---------------------------------------------------------------------------

class TestAntiClippy:
    """Verify Anti-Clippy principles in the alert queue."""

    def test_low_priority_never_auto_expands(self, queue):
        """Low-priority alerts have auto_expand=False."""
        result = queue.push_local("app_update", "Minor update", priority="low")
        assert result["auto_expand"] is False

    def test_medium_priority_never_auto_expands(self, queue):
        """Medium-priority alerts have auto_expand=False."""
        result = queue.push_local("app_update", "Some update", priority="medium")
        assert result["auto_expand"] is False
