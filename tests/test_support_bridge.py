"""
tests/test_support_bridge.py — YinyangSupportBridge Test Suite
SolaceBrowser B11 (original T17): Support bridge for classify + local handle + tickets

Tests (22 tests):
  TestClassify          (7 tests)  — local vs escalate classification
  TestHandleLocal       (7 tests)  — edit config, toggle, explain, show history, re-run
  TestCreateTicket      (4 tests)  — ticket creation, file storage, validation
  TestCheckTicketStatus (4 tests)  — status checks, not found, validation

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_support_bridge.py -v

Rung: 274177
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from inbox_outbox import InboxOutboxManager
from yinyang.support_bridge import (
    InvalidActionError,
    TicketNotFoundError,
    YinyangSupportBridge,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def apps_root(tmp_path):
    """Create a temporary apps root with a test app."""
    apps = tmp_path / "apps"
    apps.mkdir()

    # Create a test app with manifest + inbox/outbox structure
    app_dir = apps / "gmail"
    app_dir.mkdir()

    manifest = {
        "name": "Gmail",
        "description": "Gmail automation app for reading and sending emails.",
        "version": "1.0.0",
    }
    (app_dir / "manifest.yaml").write_text(
        yaml.dump(manifest), encoding="utf-8"
    )

    # Create outbox/runs with a sample run
    runs_dir = app_dir / "outbox" / "runs" / "run-001"
    runs_dir.mkdir(parents=True)
    run_data = {
        "run_id": "run-001",
        "trigger": "manual",
        "actions_summary": "Read inbox",
        "cost_usd": 0.001,
        "state": "SEALED",
        "created_at": "2026-03-01T10:00:00+00:00",
    }
    (runs_dir / "run.json").write_text(
        json.dumps(run_data, indent=2), encoding="utf-8"
    )

    return apps


@pytest.fixture
def inbox_outbox(apps_root):
    """Create an InboxOutboxManager with the test apps root."""
    return InboxOutboxManager(apps_root=apps_root)


@pytest.fixture
def solace_home(tmp_path):
    """Create a temporary solace home for ticket storage."""
    home = tmp_path / "solace_home"
    home.mkdir()
    return home


@pytest.fixture
def bridge(inbox_outbox, solace_home):
    """Create a YinyangSupportBridge instance."""
    return YinyangSupportBridge(
        inbox_outbox=inbox_outbox,
        solace_home=solace_home,
    )


# ---------------------------------------------------------------------------
# TestClassify — local vs escalate classification
# ---------------------------------------------------------------------------

class TestClassify:
    """Test classify() method for local vs escalate decisions."""

    def test_classify_edit_settings_is_local(self, bridge):
        """'edit my gmail settings' classifies as local."""
        result = bridge.classify("edit my gmail settings")
        assert result["action"] == "local"
        assert result["category"] == "edit_config"
        assert 0.0 < result["confidence"] <= 1.0

    def test_classify_bug_report_is_escalate(self, bridge):
        """'I found a bug' classifies as escalate."""
        result = bridge.classify("I found a bug in the gmail app")
        assert result["action"] == "escalate"
        assert result["category"] == "bug_report"
        assert 0.0 < result["confidence"] <= 1.0

    def test_classify_show_history_is_local(self, bridge):
        """'show run history' classifies as local."""
        result = bridge.classify("show run history for gmail")
        assert result["action"] == "local"
        assert result["category"] == "show_history"

    def test_classify_new_app_is_escalate(self, bridge):
        """'add a new app for Slack' classifies as escalate."""
        result = bridge.classify("add a new app for Slack")
        assert result["action"] == "escalate"
        assert result["category"] == "new_app"

    def test_classify_billing_is_escalate(self, bridge):
        """'billing question about my subscription' classifies as escalate."""
        result = bridge.classify("I have a billing question about my subscription")
        assert result["action"] == "escalate"
        assert result["category"] == "billing"

    def test_classify_rerun_is_local(self, bridge):
        """'re-run the last task' classifies as local."""
        result = bridge.classify("re-run the last task")
        assert result["action"] == "local"
        assert result["category"] == "rerun"

    def test_classify_empty_message_raises(self, bridge):
        """Empty message raises ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            bridge.classify("")

    def test_classify_toggle_is_local(self, bridge):
        """'turn off notifications' classifies as local toggle."""
        result = bridge.classify("turn off notifications")
        assert result["action"] == "local"
        assert result["category"] == "toggle_setting"

    def test_classify_explain_is_local(self, bridge):
        """'how does the gmail app work' classifies as local explain."""
        result = bridge.classify("how does the gmail app work")
        assert result["action"] == "local"
        assert result["category"] == "explain"

    def test_classify_unknown_defaults_to_escalate(self, bridge):
        """Unrecognized message defaults to escalate with low confidence."""
        result = bridge.classify("xyzzy completely unrelated text")
        assert result["action"] == "escalate"
        assert result["category"] == "unknown"
        assert result["confidence"] < 0.5

    def test_classify_feature_request_is_escalate(self, bridge):
        """'can you add dark mode' classifies as escalate feature request."""
        result = bridge.classify("can you add dark mode to the app")
        assert result["action"] == "escalate"
        assert result["category"] == "feature_request"


# ---------------------------------------------------------------------------
# TestHandleLocal — local action handling
# ---------------------------------------------------------------------------

class TestHandleLocal:
    """Test handle_local() for each action type."""

    def test_handle_edit_config(self, bridge):
        """edit_config action returns success with description."""
        result = bridge.handle_local(
            "gmail", "edit_config", {"key": "auto_reply", "value": "true"}
        )
        assert result["success"] is True
        assert "auto_reply" in result["result"]

    def test_handle_toggle_setting(self, bridge):
        """toggle_setting action returns success."""
        result = bridge.handle_local(
            "gmail", "toggle_setting", {"setting": "notifications", "enabled": False}
        )
        assert result["success"] is True
        assert "disabled" in result["result"]

    def test_handle_toggle_setting_enabled(self, bridge):
        """toggle_setting with enabled=True shows 'enabled'."""
        result = bridge.handle_local(
            "gmail", "toggle_setting", {"setting": "auto_send", "enabled": True}
        )
        assert result["success"] is True
        assert "enabled" in result["result"]

    def test_handle_explain(self, bridge):
        """explain action returns app description from manifest."""
        result = bridge.handle_local("gmail", "explain", {})
        assert result["success"] is True
        assert "Gmail" in result["result"]

    def test_handle_show_history(self, bridge):
        """show_history action returns run history."""
        result = bridge.handle_local("gmail", "show_history", {})
        assert result["success"] is True
        assert "run-001" in result["result"]
        assert "1 runs" in result["result"]

    def test_handle_rerun(self, bridge):
        """rerun action raises NotImplementedError (lifecycle not wired)."""
        with pytest.raises(NotImplementedError, match="Rerun queuing not yet implemented"):
            bridge.handle_local(
                "gmail", "rerun", {"run_id": "run-001"}
            )

    def test_handle_rerun_nonexistent_run(self, bridge):
        """rerun with nonexistent run_id returns failure."""
        result = bridge.handle_local(
            "gmail", "rerun", {"run_id": "nonexistent-run"}
        )
        assert result["success"] is False

    def test_handle_invalid_action_raises(self, bridge):
        """Invalid action raises InvalidActionError."""
        with pytest.raises(InvalidActionError, match="Invalid action"):
            bridge.handle_local("gmail", "fly_to_moon", {})

    def test_handle_empty_app_id_raises(self, bridge):
        """Empty app_id raises ValueError."""
        with pytest.raises(ValueError, match="app_id must not be empty"):
            bridge.handle_local("", "explain", {})

    def test_handle_edit_config_missing_key_raises(self, bridge):
        """edit_config without 'key' param raises ValueError."""
        with pytest.raises(ValueError, match="must include 'key'"):
            bridge.handle_local("gmail", "edit_config", {})

    def test_handle_toggle_missing_setting_raises(self, bridge):
        """toggle_setting without 'setting' param raises ValueError."""
        with pytest.raises(ValueError, match="must include 'setting'"):
            bridge.handle_local("gmail", "toggle_setting", {"enabled": True})

    def test_handle_rerun_missing_run_id_raises(self, bridge):
        """rerun without 'run_id' param raises ValueError."""
        with pytest.raises(ValueError, match="must include 'run_id'"):
            bridge.handle_local("gmail", "rerun", {})


# ---------------------------------------------------------------------------
# TestCreateTicket — ticket creation + persistence
# ---------------------------------------------------------------------------

class TestCreateTicket:
    """Test create_ticket() for ticket creation and local file storage."""

    def test_create_ticket_returns_ticket_id(self, bridge):
        """create_ticket returns a ticket_id starting with 'tkt-'."""
        result = bridge.create_ticket(
            description="Gmail app crashes on send",
            category="bug_report",
            context={"app_id": "gmail"},
        )
        assert result["ticket_id"].startswith("tkt-")
        assert result["status"] == "created"
        assert "url" in result
        assert "created_at" in result

    def test_create_ticket_writes_file(self, bridge, solace_home):
        """create_ticket writes a JSON file to the tickets directory."""
        result = bridge.create_ticket(
            description="Add Slack integration",
            category="feature_request",
            context={},
        )
        ticket_id = result["ticket_id"]
        ticket_path = solace_home / "support" / "tickets" / f"{ticket_id}.json"
        assert ticket_path.exists()

        raw = json.loads(ticket_path.read_text(encoding="utf-8"))
        assert raw["ticket_id"] == ticket_id
        assert raw["category"] == "feature_request"
        assert raw["description"] == "Add Slack integration"
        assert raw["status"] == "created"

    def test_create_ticket_empty_description_raises(self, bridge):
        """Empty description raises ValueError."""
        with pytest.raises(ValueError, match="description must not be empty"):
            bridge.create_ticket(
                description="",
                category="bug_report",
                context={},
            )

    def test_create_ticket_empty_category_raises(self, bridge):
        """Empty category raises ValueError."""
        with pytest.raises(ValueError, match="category must not be empty"):
            bridge.create_ticket(
                description="Something broke",
                category="",
                context={},
            )

    def test_create_ticket_url_contains_api_base(self, bridge):
        """Ticket URL uses the configured API base URL."""
        result = bridge.create_ticket(
            description="Test ticket",
            category="bug_report",
            context={},
        )
        assert "solaceagi.com" in result["url"]
        assert result["ticket_id"] in result["url"]


# ---------------------------------------------------------------------------
# TestCheckTicketStatus — status retrieval
# ---------------------------------------------------------------------------

class TestCheckTicketStatus:
    """Test check_ticket_status() for status retrieval."""

    def test_check_status_returns_created(self, bridge):
        """check_ticket_status returns 'created' for a new ticket."""
        created = bridge.create_ticket(
            description="Test ticket",
            category="bug_report",
            context={},
        )
        result = bridge.check_ticket_status(created["ticket_id"])
        assert result["ticket_id"] == created["ticket_id"]
        assert result["status"] == "created"
        assert "updated_at" in result

    def test_check_status_nonexistent_raises(self, bridge):
        """check_ticket_status for nonexistent ticket raises TicketNotFoundError."""
        with pytest.raises(TicketNotFoundError, match="Ticket not found"):
            bridge.check_ticket_status("tkt-nonexistent")

    def test_check_status_empty_id_raises(self, bridge):
        """Empty ticket_id raises ValueError."""
        with pytest.raises(ValueError, match="ticket_id must not be empty"):
            bridge.check_ticket_status("")

    def test_multiple_tickets_independent(self, bridge):
        """Multiple tickets can be created and checked independently."""
        t1 = bridge.create_ticket("Bug one", "bug_report", {})
        t2 = bridge.create_ticket("Bug two", "bug_report", {})

        s1 = bridge.check_ticket_status(t1["ticket_id"])
        s2 = bridge.check_ticket_status(t2["ticket_id"])

        assert s1["ticket_id"] != s2["ticket_id"]
        assert s1["status"] == "created"
        assert s2["status"] == "created"
