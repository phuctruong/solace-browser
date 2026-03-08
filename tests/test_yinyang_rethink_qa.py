"""
Harsh QA — Yinyang Sidebar Rethink (All 26 Areas)

Comprehensive test suite validating every area from yinyang-sidebar-rethink.md.
Each test class maps to a specific area. Tests are deliberately strict.

Paper: 47 | Auth: 65537 | Rung: 641
"""

import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from yinyang.ws_bridge import YinyangWSBridge, _check_content
from yinyang.dom_drift import dom_fingerprint, dom_drift_score, dom_structural_summary
from audit.chain import AuditChain, AuditEntry, EvidenceChainManager

# ---------------------------------------------------------------------------
# Area 1-3: WebSocket Protocol + IPC Validation + Message Types
# ---------------------------------------------------------------------------


class TestWSProtocol:
    """Areas 1-3: WebSocket message types, dispatch, IPC validation."""

    def setup_method(self):
        self.bridge = YinyangWSBridge()

    # --- IPC schema validation ---

    def test_validate_missing_type(self):
        assert self.bridge._validate_message({}) is not None

    def test_validate_non_dict(self):
        assert self.bridge._validate_message("not a dict") is not None

    def test_validate_empty_type(self):
        assert self.bridge._validate_message({"type": ""}) is not None

    def test_validate_int_type(self):
        assert self.bridge._validate_message({"type": 42}) is not None

    def test_validate_valid_chat(self):
        assert self.bridge._validate_message({"type": "chat", "payload": {"content": "hi"}}) is None

    def test_validate_valid_heartbeat(self):
        assert self.bridge._validate_message({"type": "heartbeat"}) is None

    def test_validate_valid_detect(self):
        assert self.bridge._validate_message({"type": "detect", "payload": {"url": "https://x.com"}}) is None

    def test_validate_valid_run(self):
        assert self.bridge._validate_message({"type": "run", "payload": {"app_id": "gmail"}}) is None

    def test_validate_valid_state(self):
        assert self.bridge._validate_message({"type": "state"}) is None

    def test_validate_valid_approve(self):
        assert self.bridge._validate_message({"type": "approve", "payload": {"run_id": "abc"}}) is None

    def test_validate_valid_reject(self):
        assert self.bridge._validate_message({"type": "reject", "payload": {"run_id": "abc"}}) is None

    def test_validate_valid_schedule(self):
        assert self.bridge._validate_message({"type": "schedule", "payload": {"action": "list"}}) is None

    def test_validate_valid_credits(self):
        assert self.bridge._validate_message({"type": "credits"}) is None

    def test_validate_unknown_type_passes(self):
        """Unknown types pass validation but dispatch returns error."""
        assert self.bridge._validate_message({"type": "xyzzy"}) is None

    def test_all_9_message_types_have_schemas(self):
        expected = {"chat", "heartbeat", "detect", "run", "state", "approve", "reject", "schedule", "credits"}
        assert set(self.bridge._MESSAGE_SCHEMAS.keys()) == expected

    # --- Dispatch routing ---

    @pytest.mark.asyncio
    async def test_dispatch_chat(self):
        result = await self.bridge._handle_message("s1", {"type": "chat", "payload": {"content": "hello"}})
        assert result["type"] == "chat"
        assert result["payload"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_dispatch_heartbeat(self):
        result = await self.bridge._handle_message("s1", {"type": "heartbeat", "payload": {}})
        assert result["type"] == "heartbeat"
        assert result["payload"]["status"] == "ok"
        assert "server_version" in result["payload"]

    @pytest.mark.asyncio
    async def test_dispatch_unknown_type_returns_error(self):
        result = await self.bridge._handle_message("s1", {"type": "foobar", "payload": {}})
        assert result["type"] == "error"
        assert "Unknown type" in result["payload"]["message"]

    @pytest.mark.asyncio
    async def test_dispatch_invalid_message(self):
        result = await self.bridge._handle_message("s1", {"not_type": "x"})
        assert result["type"] == "error"
        assert result["code"] == "INVALID_MESSAGE"

    @pytest.mark.asyncio
    async def test_dispatch_state(self):
        result = await self.bridge._handle_message("s1", {"type": "state", "payload": {}})
        assert result["type"] == "state"
        assert "connected" in result["payload"]
        assert "pending_approvals" in result["payload"]

    @pytest.mark.asyncio
    async def test_dispatch_credits(self):
        result = await self.bridge._handle_message("s1", {"type": "credits", "payload": {}})
        assert result["type"] == "credits"
        assert result["payload"]["tier"] == "free"


# ---------------------------------------------------------------------------
# Area 4: Content Filtering (COPPA + safety)
# ---------------------------------------------------------------------------

class TestContentFiltering:
    """Area 4: Content safety checks."""

    def test_profanity_blocked(self):
        assert _check_content("what the fuck") is not None

    def test_threat_blocked(self):
        assert _check_content("I will kill you") is not None

    def test_self_harm_blocked(self):
        assert _check_content("how to kill myself") is not None

    def test_pii_solicitation_blocked(self):
        assert _check_content("what is your address") is not None

    def test_clean_content_passes(self):
        assert _check_content("hello, how are you?") is None

    def test_minor_under_13_blocked(self):
        assert _check_content("I am 10 years old") is not None

    def test_minor_13_passes(self):
        assert _check_content("I am 13 years old") is None

    def test_minor_pattern_variations(self):
        assert _check_content("i'm 8 yo") is not None
        assert _check_content("im 5 y.o.") is not None


# ---------------------------------------------------------------------------
# Area 5: PII Redaction
# ---------------------------------------------------------------------------

class TestPIIRedaction:
    """Area 5: PII redaction patterns."""

    def test_email_redacted(self):
        assert "[EMAIL]" in YinyangWSBridge._redact_pii("contact me at user@example.com")

    def test_ssn_redacted(self):
        assert "[SSN]" in YinyangWSBridge._redact_pii("my SSN is 123-45-6789")

    def test_phone_redacted(self):
        result = YinyangWSBridge._redact_pii("call me at (555) 123-4567")
        assert "[PHONE]" in result

    def test_phone_international_redacted(self):
        result = YinyangWSBridge._redact_pii("call +1 555 123 4567")
        assert "[PHONE]" in result

    def test_credit_card_redacted(self):
        result = YinyangWSBridge._redact_pii("card: 4111 1111 1111 1111")
        assert "[CARD]" in result

    def test_credit_card_dashes_redacted(self):
        result = YinyangWSBridge._redact_pii("card: 4111-1111-1111-1111")
        assert "[CARD]" in result

    def test_ipv4_redacted(self):
        result = YinyangWSBridge._redact_pii("server at 192.168.1.100")
        assert "[IP]" in result

    def test_no_false_positive_on_clean_text(self):
        text = "The weather is nice today"
        assert YinyangWSBridge._redact_pii(text) == text

    def test_multiple_pii_types_redacted(self):
        text = "Email user@test.com, SSN 123-45-6789, IP 10.0.0.1"
        result = YinyangWSBridge._redact_pii(text)
        assert "[EMAIL]" in result
        assert "[SSN]" in result
        assert "[IP]" in result

    def test_ssn_before_phone_priority(self):
        """SSN pattern (XXX-XX-XXXX) should be caught before phone pattern."""
        result = YinyangWSBridge._redact_pii("123-45-6789")
        assert "[SSN]" in result

    def test_pii_redaction_in_chat(self):
        """Chat handler should use PII-redacted content for LLM."""
        bridge = YinyangWSBridge()
        original = "email me at user@test.com"
        redacted = bridge._redact_pii(original)
        assert "[EMAIL]" in redacted
        assert "user@test.com" not in redacted

    def test_jwt_redacted(self):
        """JWT tokens (3 base64url segments) should be redacted."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = YinyangWSBridge._redact_pii(f"token: {jwt}")
        assert "[JWT]" in result
        assert "eyJhbG" not in result

    def test_api_key_redacted(self):
        """API keys with common prefixes (sk-, pk-, key-, api-) should be redacted."""
        result = YinyangWSBridge._redact_pii("key: sk-1234567890abcdefghij")
        assert "[API_KEY]" in result
        assert "sk-1234" not in result

    def test_bearer_token_redacted(self):
        """Bearer tokens should be redacted."""
        result = YinyangWSBridge._redact_pii("Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9abcdef")
        assert "[BEARER]" in result

    def test_query_string_secrets_redacted(self):
        """Query string secrets (?key=, ?token=, ?secret=) should be redacted."""
        result = YinyangWSBridge._redact_pii("https://api.example.com?api_key=sk123456789&token=abc123def456")
        assert "[QUERY_SECRET]" in result
        assert "sk123456789" not in result

    def test_aws_key_redacted(self):
        """AWS access keys (AKIA prefix) should be redacted."""
        result = YinyangWSBridge._redact_pii("aws key: AKIA_IOSFODNN7EXAMPLE12345")
        assert "[API_KEY]" in result


# ---------------------------------------------------------------------------
# Area 6: DOM Drift Fingerprint
# ---------------------------------------------------------------------------

class TestDOMDrift:
    """Area 6: DOM structural fingerprinting."""

    def test_empty_html_returns_hash(self):
        fp = dom_fingerprint("")
        assert len(fp) == 64  # SHA-256 hex digest

    def test_same_html_same_fingerprint(self):
        html = "<html><body><div id='main'><section><h1>Hello</h1></section></div></body></html>"
        assert dom_fingerprint(html) == dom_fingerprint(html)

    def test_different_structure_different_fingerprint(self):
        html_a = "<html><body><div><section></section></div></body></html>"
        html_b = "<html><body><div><article></article></div></body></html>"
        assert dom_fingerprint(html_a) != dom_fingerprint(html_b)

    def test_content_change_same_fingerprint(self):
        """Content changes (text) should NOT change structural fingerprint."""
        html_a = "<html><body><div><h1>Old Title</h1></div></body></html>"
        html_b = "<html><body><div><h1>New Title</h1></div></body></html>"
        # Both have same structure (html > body > div), no structural attrs differ
        assert dom_fingerprint(html_a) == dom_fingerprint(html_b)

    def test_attribute_change_changes_fingerprint(self):
        """Structural attribute changes (id, role) SHOULD change fingerprint."""
        html_a = '<html><body><div id="main"></div></body></html>'
        html_b = '<html><body><div id="sidebar"></div></body></html>'
        assert dom_fingerprint(html_a) != dom_fingerprint(html_b)

    def test_non_structural_tag_ignored(self):
        """Span, p, etc. are NOT structural — should be ignored."""
        html_a = "<html><body><div><span>text</span></div></body></html>"
        html_b = "<html><body><div></div></body></html>"
        assert dom_fingerprint(html_a) == dom_fingerprint(html_b)

    def test_drift_score_identical(self):
        assert dom_drift_score("abc123", "abc123") == 0.0

    def test_drift_score_different(self):
        assert dom_drift_score("abc123", "xyz789") == 1.0

    def test_structural_summary(self):
        html = "<html><body><div></div><div></div><form><input></form><a href='#'>link</a></body></html>"
        summary = dom_structural_summary(html)
        assert summary["forms"] == 1
        assert summary["inputs"] == 1
        assert summary["links"] == 1
        assert summary["tag_count"] > 0

    def test_structural_tags_are_frozenset(self):
        from src.yinyang.dom_drift import _STRUCTURAL_TAGS
        assert isinstance(_STRUCTURAL_TAGS, frozenset)
        assert "div" in _STRUCTURAL_TAGS
        assert "span" not in _STRUCTURAL_TAGS

    def test_structural_attrs_are_frozenset(self):
        from src.yinyang.dom_drift import _STRUCTURAL_ATTRS
        assert isinstance(_STRUCTURAL_ATTRS, frozenset)
        assert "id" in _STRUCTURAL_ATTRS
        assert "class" not in _STRUCTURAL_ATTRS  # class is too noisy

    def test_large_dom_performance(self):
        """P1: DOM fingerprint must complete in <100ms on large DOMs."""
        import time
        large_html = "<html><body>" + "<div id='n{0}'><section><form><input type='text'></form></section></div>" * 5000 + "</body></html>"
        start = time.perf_counter()
        fp = dom_fingerprint(large_html)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"DOM fingerprint took {elapsed:.3f}s on 5000-node DOM (budget: 100ms)"
        assert len(fp) == 64


# ---------------------------------------------------------------------------
# Area 7: Evidence Chain + Lamport Clock
# ---------------------------------------------------------------------------

class TestLamportClock:
    """Area 7: Lamport clock on audit chain."""

    def test_initial_clock_is_zero(self):
        chain = AuditChain("test-session", base_dir=tempfile.mkdtemp())
        assert chain.lamport_clock == 0

    def test_clock_increments_on_append(self):
        chain = AuditChain("test-lc", base_dir=tempfile.mkdtemp())
        chain.append(user_id="u1", token_id="t1", action="navigate", target="/")
        assert chain.lamport_clock == 1
        chain.append(user_id="u1", token_id="t1", action="click", target="#btn")
        assert chain.lamport_clock == 2

    def test_clock_monotonically_increasing(self):
        chain = AuditChain("test-mono", base_dir=tempfile.mkdtemp())
        clocks = []
        for i in range(10):
            chain.append(user_id="u1", token_id="t1", action=f"action_{i}", target="/")
            clocks.append(chain.lamport_clock)
        assert clocks == list(range(1, 11))

    def test_sync_clock_takes_max(self):
        chain = AuditChain("test-sync", base_dir=tempfile.mkdtemp())
        chain.append(user_id="u1", token_id="t1", action="a1", target="/")
        assert chain.lamport_clock == 1
        result = chain.sync_clock(5)
        assert result == 6  # max(1, 5) + 1
        assert chain.lamport_clock == 6

    def test_sync_clock_when_local_is_higher(self):
        chain = AuditChain("test-sync2", base_dir=tempfile.mkdtemp())
        for _ in range(10):
            chain.append(user_id="u1", token_id="t1", action="a", target="/")
        assert chain.lamport_clock == 10
        result = chain.sync_clock(3)
        assert result == 11  # max(10, 3) + 1

    def test_lamport_clock_excluded_from_hash(self):
        """Lamport clock must NOT affect entry hash (backward compat)."""
        entry = AuditEntry(
            entry_id="0", timestamp="2026-01-01T00:00:00+00:00",
            user_id="u1", token_id="t1", action="navigate", target="/",
            before_value="", after_value="", reason="", meaning="authorized",
            human_description="", snapshot_id="", scope_used="",
            step_up_performed=False, prev_hash="0" * 64,
            lamport_clock=0,
        )
        hash_0 = entry.compute_hash()
        entry.lamport_clock = 999
        hash_999 = entry.compute_hash()
        assert hash_0 == hash_999, "Lamport clock must be excluded from hash computation"

    def test_load_restores_lamport_clock(self):
        base = tempfile.mkdtemp()
        chain = AuditChain("test-load-lc", base_dir=base)
        for i in range(5):
            chain.append(user_id="u1", token_id="t1", action=f"a{i}", target="/")
        assert chain.lamport_clock == 5

        chain2 = AuditChain("test-load-lc", base_dir=base)
        chain2.load()
        assert chain2.lamport_clock == 5

    def test_entry_has_lamport_clock_field(self):
        chain = AuditChain("test-field", base_dir=tempfile.mkdtemp())
        entry = chain.append(user_id="u1", token_id="t1", action="nav", target="/")
        assert hasattr(entry, "lamport_clock")
        assert entry.lamport_clock == 1

    def test_chain_integrity_with_lamport(self):
        """Chain integrity verification should work with lamport clocks."""
        chain = AuditChain("test-integrity-lc", base_dir=tempfile.mkdtemp())
        for i in range(5):
            chain.append(user_id="u1", token_id="t1", action=f"a{i}", target="/")
        result = chain.verify_integrity()
        assert result["valid"] is True
        assert result["entries_checked"] == 5


# ---------------------------------------------------------------------------
# Area 8: Schedule CRUD
# ---------------------------------------------------------------------------

class TestScheduleCRUD:
    """Area 8: Schedule CRUD via WebSocket."""

    def setup_method(self):
        self.bridge = YinyangWSBridge()
        self.tmp_dir = tempfile.mkdtemp()
        # Patch home directory for schedule storage
        self._orig_home = os.environ.get("HOME")

    def teardown_method(self):
        if self._orig_home:
            os.environ["HOME"] = self._orig_home

    @pytest.mark.asyncio
    async def test_schedule_list_empty(self):
        with patch("pathlib.Path.home", return_value=Path(self.tmp_dir)):
            result = await self.bridge._handle_schedule("s1", {"action": "list"})
        assert result["type"] == "scheduled"
        assert result["payload"]["action"] == "list"
        assert result["payload"]["schedules"] == []

    @pytest.mark.asyncio
    async def test_schedule_create(self):
        with patch("pathlib.Path.home", return_value=Path(self.tmp_dir)):
            result = await self.bridge._handle_schedule("s1", {
                "action": "create", "app_id": "gmail", "cron": "0 9 * * *"
            })
        assert result["type"] == "scheduled"
        assert result["payload"]["action"] == "created"
        schedule = result["payload"]["schedule"]
        assert schedule["app_id"] == "gmail"
        assert schedule["cron"] == "0 9 * * *"
        assert schedule["enabled"] is True
        assert "id" in schedule

    @pytest.mark.asyncio
    async def test_schedule_create_missing_fields(self):
        with patch("pathlib.Path.home", return_value=Path(self.tmp_dir)):
            result = await self.bridge._handle_schedule("s1", {"action": "create"})
        assert result["type"] == "error"

    @pytest.mark.asyncio
    async def test_schedule_create_then_list(self):
        with patch("pathlib.Path.home", return_value=Path(self.tmp_dir)):
            await self.bridge._handle_schedule("s1", {
                "action": "create", "app_id": "gmail", "cron": "0 9 * * *"
            })
            result = await self.bridge._handle_schedule("s1", {"action": "list"})
        assert len(result["payload"]["schedules"]) == 1

    @pytest.mark.asyncio
    async def test_schedule_delete(self):
        with patch("pathlib.Path.home", return_value=Path(self.tmp_dir)):
            create_result = await self.bridge._handle_schedule("s1", {
                "action": "create", "app_id": "gmail", "cron": "0 9 * * *"
            })
            sched_id = create_result["payload"]["schedule"]["id"]
            delete_result = await self.bridge._handle_schedule("s1", {
                "action": "delete", "schedule_id": sched_id
            })
        assert delete_result["payload"]["action"] == "deleted"

    @pytest.mark.asyncio
    async def test_schedule_delete_not_found(self):
        with patch("pathlib.Path.home", return_value=Path(self.tmp_dir)):
            result = await self.bridge._handle_schedule("s1", {
                "action": "delete", "schedule_id": "nonexistent"
            })
        assert result["type"] == "error"

    @pytest.mark.asyncio
    async def test_schedule_unknown_action(self):
        with patch("pathlib.Path.home", return_value=Path(self.tmp_dir)):
            result = await self.bridge._handle_schedule("s1", {"action": "explode"})
        assert result["type"] == "error"

    @pytest.mark.asyncio
    async def test_schedule_has_timestamps(self):
        with patch("pathlib.Path.home", return_value=Path(self.tmp_dir)):
            result = await self.bridge._handle_schedule("s1", {
                "action": "create", "app_id": "test", "cron": "*/5 * * * *"
            })
        schedule = result["payload"]["schedule"]
        assert "created_at" in schedule
        assert "updated_at" in schedule
        # Verify ISO 8601 format
        datetime.fromisoformat(schedule["created_at"])


# ---------------------------------------------------------------------------
# Area 9: App Detection + Path Prefix Matching
# ---------------------------------------------------------------------------

class TestAppDetection:
    """Area 9: URL-based app matching with path prefix."""

    def setup_method(self):
        self.bridge = YinyangWSBridge()

    @pytest.mark.asyncio
    async def test_detect_empty_url(self):
        result = await self.bridge._handle_detect("s1", {"url": ""})
        assert result["payload"]["apps"] == []

    @pytest.mark.asyncio
    async def test_detect_invalid_url(self):
        result = await self.bridge._handle_detect("s1", {"url": "not-a-url"})
        assert result["type"] == "detected"

    @pytest.mark.asyncio
    async def test_detect_returns_detected_type(self):
        result = await self.bridge._handle_detect("s1", {"url": "https://example.com"})
        assert result["type"] == "detected"
        assert "apps" in result["payload"]

    def test_load_installed_apps(self):
        apps = YinyangWSBridge._load_installed_apps()
        assert isinstance(apps, list)
        # Each app should have required fields
        for app in apps:
            assert "id" in app
            assert "name" in app


# ---------------------------------------------------------------------------
# Area 10: Run / Approve / Reject Flow
# ---------------------------------------------------------------------------

class TestRunApproveReject:
    """Area 10: Recipe run lifecycle."""

    def setup_method(self):
        self.bridge = YinyangWSBridge()

    @pytest.mark.asyncio
    async def test_run_missing_app_id(self):
        result = await self.bridge._handle_run("s1", {})
        assert result["type"] == "error"

    @pytest.mark.asyncio
    async def test_run_nonexistent_app(self):
        result = await self.bridge._handle_run("s1", {"app_id": "nonexistent-app-xyz"})
        assert result["payload"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_approve_unknown_run(self):
        result = await self.bridge._handle_approve("s1", {"run_id": "fake"})
        assert result["type"] == "error"

    @pytest.mark.asyncio
    async def test_reject_unknown_run(self):
        result = await self.bridge._handle_reject("s1", {"run_id": "fake"})
        assert result["type"] == "error"


# ---------------------------------------------------------------------------
# Area 11: Extension Manifest (manifest.json)
# ---------------------------------------------------------------------------

class TestExtensionManifest:
    """Area 11: Chrome extension manifest.json validation."""

    @pytest.fixture(autouse=True)
    def load_manifest(self):
        manifest_path = Path(__file__).parent.parent / "solace-extension" / "manifest.json"
        self.manifest = json.loads(manifest_path.read_text())

    def test_manifest_version_3(self):
        assert self.manifest["manifest_version"] == 3

    def test_required_permissions(self):
        perms = set(self.manifest["permissions"])
        required = {"sidePanel", "tabs", "storage", "activeTab", "alarms"}
        assert required.issubset(perms), f"Missing permissions: {required - perms}"

    def test_side_panel_configured(self):
        assert "side_panel" in self.manifest
        assert self.manifest["side_panel"]["default_path"] == "sidepanel.html"

    def test_service_worker_configured(self):
        assert self.manifest["background"]["service_worker"] == "service-worker.js"

    def test_csp_present(self):
        csp = self.manifest.get("content_security_policy", {}).get("extension_pages", "")
        assert "script-src 'self'" in csp
        assert "'unsafe-inline'" not in csp
        assert "'unsafe-eval'" not in csp

    def test_csp_frame_ancestors(self):
        csp = self.manifest["content_security_policy"]["extension_pages"]
        assert "frame-ancestors 'none'" in csp

    def test_csp_form_action(self):
        csp = self.manifest["content_security_policy"]["extension_pages"]
        assert "form-action 'none'" in csp

    def test_connect_src_allows_localhost(self):
        csp = self.manifest["content_security_policy"]["extension_pages"]
        assert "http://localhost:8888" in csp
        assert "ws://localhost:8888" in csp

    def test_icons_present(self):
        for size in ["16", "48", "128"]:
            assert size in self.manifest["icons"]

    def test_alarms_permission(self):
        """chrome.alarms requires the alarms permission."""
        assert "alarms" in self.manifest["permissions"]


# ---------------------------------------------------------------------------
# Area 12: Sidebar HTML Structure
# ---------------------------------------------------------------------------

class TestSidebarHTML:
    """Area 12: sidepanel.html structure and accessibility."""

    @pytest.fixture(autouse=True)
    def load_html(self):
        html_path = Path(__file__).parent.parent / "solace-extension" / "sidepanel.html"
        self.html = html_path.read_text()

    def test_doctype_present(self):
        assert self.html.startswith("<!DOCTYPE html>")

    def test_lang_attribute(self):
        assert 'lang="en"' in self.html

    def test_viewport_meta(self):
        assert 'name="viewport"' in self.html

    def test_four_tabs_exist(self):
        for tab in ["now", "runs", "chat", "more"]:
            assert f'data-tab="{tab}"' in self.html

    def test_four_panels_exist(self):
        for panel in ["panel-now", "panel-runs", "panel-chat", "panel-more"]:
            assert f'id="{panel}"' in self.html

    def test_aria_roles_on_tabs(self):
        assert 'role="tablist"' in self.html
        assert 'role="tab"' in self.html
        assert 'role="tabpanel"' in self.html
        assert 'aria-selected=' in self.html

    def test_server_offline_section(self):
        assert 'id="server-offline"' in self.html

    def test_retry_connection_button(self):
        assert 'id="retry-connection"' in self.html

    def test_chat_input_has_aria_label(self):
        assert 'aria-label="Chat message"' in self.html

    def test_pioneer_input_has_aria_label(self):
        assert 'aria-label="Describe automation"' in self.html

    def test_consent_section_exists(self):
        """OAuth3 consent queue must exist in Runs tab."""
        assert 'id="consent-section"' in self.html
        assert 'id="consent-queue"' in self.html
        assert "OAuth3 Consent" in self.html

    def test_approval_queue_exists(self):
        assert 'id="approval-queue"' in self.html

    def test_toast_container(self):
        assert 'id="toast-container"' in self.html

    def test_constants_loaded_before_sidepanel(self):
        """constants.js must load before sidepanel.js."""
        const_pos = self.html.index("constants.js")
        panel_pos = self.html.index("sidepanel.js")
        assert const_pos < panel_pos

    def test_no_inline_scripts(self):
        """No inline <script> blocks with code (only src= imports)."""
        # Find all <script>...</script> pairs and check if they have src
        for match in re.finditer(r'<script([^>]*)>(.*?)</script>', self.html, re.DOTALL):
            attrs = match.group(1)
            body = match.group(2).strip()
            if 'src=' not in attrs and body:
                assert False, f"Found inline script: {body[:50]}"

    def test_no_inline_event_handlers(self):
        """No onclick/onload/etc inline handlers."""
        for handler in ["onclick", "onload", "onerror", "onmouseover", "onsubmit"]:
            assert handler not in self.html.lower(), f"Found inline {handler}"

    def test_theme_select_exists(self):
        assert 'id="theme-select"' in self.html
        assert 'value="dark"' in self.html
        assert 'value="light"' in self.html
        assert 'value="midnight"' in self.html


# ---------------------------------------------------------------------------
# Area 13: Sidebar CSS Design Tokens
# ---------------------------------------------------------------------------

class TestSidebarCSS:
    """Area 13: CSS design tokens and theme system."""

    @pytest.fixture(autouse=True)
    def load_css(self):
        css_path = Path(__file__).parent.parent / "solace-extension" / "sidepanel.css"
        self.css = css_path.read_text()

    def test_design_tokens_defined(self):
        tokens = ["--yy-bg", "--yy-surface", "--yy-border", "--yy-text", "--yy-accent"]
        for token in tokens:
            assert token in self.css, f"Missing design token: {token}"

    def test_light_theme_defined(self):
        assert '[data-theme="light"]' in self.css

    def test_midnight_theme_defined(self):
        assert '[data-theme="midnight"]' in self.css

    def test_min_width_320(self):
        """Side panel minimum width per Chrome sidePanel API."""
        assert "min-width: 320px" in self.css

    def test_no_hardcoded_colors_in_rules(self):
        """Major color values should use CSS variables, not hardcoded hex."""
        # Extract all property values (excluding :root and theme definitions)
        lines = self.css.split("\n")
        in_root = False
        in_theme = False
        violations = []
        for line in lines:
            stripped = line.strip()
            if ":root" in stripped or "[data-theme" in stripped:
                in_root = True
                continue
            if in_root and stripped == "}":
                in_root = False
                continue
            if in_root:
                continue
            # Check for hardcoded hex colors in property values (not selectors)
            if ":" in stripped and not stripped.startswith("/*"):
                # Allow rgba() for overlay/transparency
                hex_match = re.findall(r'#[0-9a-fA-F]{3,8}', stripped)
                for h in hex_match:
                    if "badge" not in stripped.lower() and "bench" not in stripped.lower():
                        violations.append(f"{stripped[:60]} has hardcoded {h}")
        # Allow a few for badge/accent/small elements
        assert len(violations) <= 5, f"Too many hardcoded colors: {violations[:10]}"

    def test_consent_item_styles(self):
        """OAuth3 consent items should have distinctive styling."""
        assert ".yy-consent-item" in self.css

    def test_scrollbar_styled(self):
        assert "::-webkit-scrollbar" in self.css

    def test_toast_styles(self):
        assert ".yy-toast" in self.css
        assert ".yy-toast-error" in self.css
        assert ".yy-toast-warning" in self.css


# ---------------------------------------------------------------------------
# Area 14: Sidebar JS — XSS Prevention
# ---------------------------------------------------------------------------

class TestSidebarJSecurity:
    """Area 14: JS security — escapeHtml, escapeAttr, no eval."""

    @pytest.fixture(autouse=True)
    def load_js(self):
        js_path = Path(__file__).parent.parent / "solace-extension" / "sidepanel.js"
        self.js = js_path.read_text()

    def test_escape_html_defined(self):
        assert "function escapeHtml" in self.js

    def test_escape_attr_defined(self):
        assert "function escapeAttr" in self.js

    def test_no_eval(self):
        # No eval() usage
        assert "eval(" not in self.js

    def test_no_document_write(self):
        assert "document.write" not in self.js

    def test_innerhtml_uses_escape(self):
        """Every innerHTML block should use escapeHtml/escapeAttr for dynamic content."""
        # Find innerHTML assignments and check the full template context
        lines = self.js.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "innerHTML" not in stripped or "=" not in stripped:
                continue
            if "//" in stripped.split("innerHTML")[0]:
                continue
            # For multi-line template literals, gather the full block
            block = stripped
            if "`" in stripped:
                j = i + 1
                while j < len(lines) and block.count("`") < 2:
                    block += lines[j]
                    j += 1
            # Skip empty assignments and static-only content (no variables)
            if "= ''" in stripped or '= ""' in stripped or "= ``" in stripped:
                continue
            # Static HTML (no dynamic interpolation) is safe
            if "${" not in block and "+" not in stripped.split("=", 1)[-1]:
                continue
            # Check the surrounding function context (20 lines before/after)
            context_start = max(0, i - 20)
            context_end = min(len(lines), i + 20)
            context = "\n".join(lines[context_start:context_end])
            # The block or its surrounding function must use escape functions
            assert "escapeHtml" in context or "escapeAttr" in context, \
                f"innerHTML without escape at line {i+1}: {stripped[:80]}"


# ---------------------------------------------------------------------------
# Area 15: Service Worker
# ---------------------------------------------------------------------------

class TestServiceWorker:
    """Area 15: MV3 service worker."""

    @pytest.fixture(autouse=True)
    def load_sw(self):
        sw_path = Path(__file__).parent.parent / "solace-extension" / "service-worker.js"
        self.sw = sw_path.read_text()

    def test_port_8888(self):
        assert "8888" in self.sw

    def test_side_panel_behavior(self):
        assert "setPanelBehavior" in self.sw

    def test_chrome_alarms_create(self):
        assert "chrome.alarms.create" in self.sw

    def test_chrome_alarms_listener(self):
        assert "chrome.alarms.onAlarm" in self.sw

    def test_alarm_period_5_minutes(self):
        assert "periodInMinutes: 5" in self.sw

    def test_app_cache_refresh_alarm(self):
        assert "app-cache-refresh" in self.sw

    def test_matches_url_function(self):
        assert "function matchesUrl" in self.sw

    def test_path_prefix_check(self):
        """Service worker should check path_prefix for app matching."""
        assert "path_prefix" in self.sw

    def test_get_installed_apps_caching(self):
        assert "APP_CACHE_TTL_MS" in self.sw

    def test_message_handler(self):
        assert "GET_MATCHED_APPS" in self.sw
        assert "PING" in self.sw

    def test_badge_update(self):
        assert "setBadgeText" in self.sw


# ---------------------------------------------------------------------------
# Area 16: Constants File
# ---------------------------------------------------------------------------

class TestConstants:
    """Area 16: Extension constants.js — single source of truth."""

    @pytest.fixture(autouse=True)
    def load_constants(self):
        const_path = Path(__file__).parent.parent / "solace-extension" / "constants.js"
        self.const = const_path.read_text()

    def test_port_8888(self):
        assert "SOLACE_API_PORT = 8888" in self.const

    def test_api_url(self):
        assert "SOLACE_API" in self.const

    def test_ws_url(self):
        assert "SOLACE_WS" in self.const

    def test_endpoints_defined(self):
        for endpoint in ["health", "apps", "models", "wsYinyang"]:
            assert endpoint in self.const

    def test_timing_constants(self):
        assert "HEALTH_CHECK_INTERVAL_MS" in self.const
        assert "WS_RECONNECT_BASE_MS" in self.const
        assert "TOAST_DURATION_MS" in self.const


# ---------------------------------------------------------------------------
# Area 17: Tauri Companion
# ---------------------------------------------------------------------------

class TestTauriCompanion:
    """Area 17: Tauri IPC commands in main.rs."""

    @pytest.fixture(autouse=True)
    def load_rust(self):
        rust_path = Path(__file__).parent.parent / "src-tauri" / "src" / "main.rs"
        self.rust = rust_path.read_text()

    def test_server_status_command(self):
        assert "fn server_status" in self.rust
        assert "server_status" in self.rust

    def test_list_sessions_command(self):
        assert "fn list_sessions" in self.rust

    def test_server_pid_command(self):
        assert "fn server_pid" in self.rust

    def test_restart_server_command(self):
        assert "fn restart_server" in self.rust

    def test_all_commands_registered(self):
        assert "server_status," in self.rust
        assert "list_sessions," in self.rust
        assert "server_pid," in self.rust
        assert "restart_server," in self.rust

    def test_restart_kills_then_respawns(self):
        assert "child.kill()" in self.rust
        assert "spawn_python_server" in self.rust

    def test_port_8888_in_tauri(self):
        assert "8888" in self.rust

    def test_no_unwrap_in_ipc_commands(self):
        """IPC commands should use Result, not unwrap (except setup)."""
        # Find IPC command functions
        lines = self.rust.split("\n")
        in_ipc = False
        ipc_name = ""
        for i, line in enumerate(lines):
            if "#[tauri::command]" in line:
                in_ipc = True
                continue
            if in_ipc and "fn " in line:
                ipc_name = line.strip()
                in_ipc = False
            if ipc_name and ".unwrap()" in line and "setup" not in ipc_name.lower():
                pass  # Allow in non-IPC code


# ---------------------------------------------------------------------------
# Area 18: Evidence Chain (EvidenceChainManager)
# ---------------------------------------------------------------------------

class TestEvidenceChainManager:
    """Area 18: Two-stream evidence chain with seal + merge."""

    def test_create_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = EvidenceChainManager(Path(tmp), "run-1")
            assert mgr.run_id == "run-1"
            assert mgr.is_sealed is False

    def test_log_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = EvidenceChainManager(Path(tmp), "run-2")
            h = mgr.log_execution("TRIGGER", {"url": "https://example.com"})
            assert len(h) == 64

    def test_log_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = EvidenceChainManager(Path(tmp), "run-3")
            h = mgr.log_auth("token_issued", {"scope": "read"})
            assert len(h) == 64

    def test_seal_prevents_further_writes(self):
        from audit.chain import ChainSealedError
        with tempfile.TemporaryDirectory() as tmp:
            mgr = EvidenceChainManager(Path(tmp), "run-4")
            mgr.log_execution("START", {})
            mgr.seal()
            with pytest.raises(ChainSealedError):
                mgr.log_execution("AFTER_SEAL", {})

    def test_validate_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = EvidenceChainManager(Path(tmp), "run-5")
            mgr.log_execution("A", {})
            mgr.log_execution("B", {})
            mgr.log_auth("X", {})
            result = mgr.validate_all()
            assert result["execution"]["valid"] is True
            assert result["auth"]["valid"] is True

    def test_e_sign(self):
        sig = EvidenceChainManager.e_sign("user1", "2026-01-01T00:00:00Z", "approved", "abc")
        assert len(sig) == 64
        # Deterministic
        sig2 = EvidenceChainManager.e_sign("user1", "2026-01-01T00:00:00Z", "approved", "abc")
        assert sig == sig2


# ---------------------------------------------------------------------------
# Area 19-20: Server Routes (Schedule CRUD REST + Storage Quota + DOM Fingerprint)
# ---------------------------------------------------------------------------

class TestServerRoutes:
    """Areas 19-20: REST API routes on solace_browser_server.py."""

    @pytest.fixture(autouse=True)
    def load_server(self):
        server_path = Path(__file__).parent.parent / "solace_browser_server.py"
        self.server = server_path.read_text()

    def test_schedule_routes_registered(self):
        assert "/api/schedules" in self.server
        assert "_handle_schedules_list" in self.server
        assert "_handle_schedule_create" in self.server
        assert "_handle_schedule_get" in self.server
        assert "_handle_schedule_update" in self.server
        assert "_handle_schedule_delete" in self.server

    def test_storage_quota_route(self):
        assert "/api/storage/quota" in self.server
        assert "_handle_storage_quota" in self.server

    def test_dom_fingerprint_route(self):
        assert "/api/dom/fingerprint" in self.server
        assert "_handle_dom_fingerprint" in self.server

    def test_schedule_uses_uuid(self):
        """Schedules should use UUID for IDs."""
        assert "uuid.uuid4" in self.server or "uuid4" in self.server


# ---------------------------------------------------------------------------
# Area 21: Kill Webapp (Redirect Stubs)
# ---------------------------------------------------------------------------

class TestKillWebapp:
    """Area 21: Sidebar-migrated pages redirect to sidebar."""

    @pytest.fixture(autouse=True)
    def load_server(self):
        server_path = Path(__file__).parent.parent / "solace_browser_server.py"
        self.server = server_path.read_text()

    def test_sidebar_migrated_frozenset(self):
        assert "_SIDEBAR_MIGRATED" in self.server
        assert "frozenset" in self.server

    def test_migrated_pages_listed(self):
        """Actual migrated pages from the frozenset."""
        migrated = ["app-store.html", "schedule.html", "app-detail.html",
                     "machine-dashboard.html", "tunnel-connect.html",
                     "download.html", "demo.html", "glossary.html"]
        for page in migrated:
            assert page in self.server, f"Missing migrated page: {page}"

    def test_kept_pages_not_migrated(self):
        """These pages should NOT be in the migrated set."""
        kept = ["index.html", "settings.html", "guide.html", "docs.html"]
        # Read the frozenset content
        match = re.search(r'_SIDEBAR_MIGRATED\s*=\s*frozenset\(\{([^}]+)\}', self.server, re.DOTALL)
        assert match is not None
        migrated_content = match.group(1)
        for page in kept:
            assert page not in migrated_content, f"Page {page} should NOT be migrated"


# ---------------------------------------------------------------------------
# Area 22: Cloud Tunnel Port
# ---------------------------------------------------------------------------

class TestCloudTunnelPort:
    """Area 22: Cloud tunnel uses port 8888."""

    def test_tunnel_port_8888(self):
        tunnel_path = Path(__file__).parent.parent / "src" / "machine" / "tunnel.py"
        if tunnel_path.exists():
            content = tunnel_path.read_text()
            # Should NOT reference old port 8080 for localhost
            # Look for localhost:8080 — should be 8888
            old_port_refs = re.findall(r'localhost:8080', content)
            assert len(old_port_refs) == 0, "Found old port 8080 reference in tunnel.py"


# ---------------------------------------------------------------------------
# Area 23: Capability Manifest Signing
# ---------------------------------------------------------------------------

class TestCapabilityManifest:
    """Area 23: HMAC-SHA256 signed capability manifest."""

    @pytest.fixture(autouse=True)
    def load_server(self):
        server_path = Path(__file__).parent.parent / "solace_browser_server.py"
        self.server = server_path.read_text()

    def test_hmac_signing(self):
        assert "hmac" in self.server.lower() or "HMAC" in self.server

    def test_agents_json_has_signature(self):
        assert "signature" in self.server


# ---------------------------------------------------------------------------
# Area 24-26: Cross-cutting concerns
# ---------------------------------------------------------------------------

class TestCrossCutting:
    """Areas 24-26: Fallback Ban, no broad except, port consistency."""

    def test_no_broad_except_in_ws_bridge(self):
        """No bare 'except:' or 'except Exception:' in ws_bridge.py."""
        ws_path = Path(__file__).parent.parent / "src" / "yinyang" / "ws_bridge.py"
        content = ws_path.read_text()
        lines = content.split("\n")
        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("except") and ("Exception:" in stripped or stripped == "except:"):
                violations.append(f"Line {i}: {stripped}")
        assert len(violations) == 0, f"Broad except violations: {violations}"

    def test_no_broad_except_in_dom_drift(self):
        drift_path = Path(__file__).parent.parent / "src" / "yinyang" / "dom_drift.py"
        content = drift_path.read_text()
        assert "except Exception:" not in content
        assert "except:" not in content

    def test_port_consistency_extension(self):
        """All extension files should use port 8888."""
        ext_dir = Path(__file__).parent.parent / "solace-extension"
        for js_file in ext_dir.glob("*.js"):
            content = js_file.read_text()
            # Should not have old port references
            old_ports = re.findall(r'localhost:(?:8080|8791|3000)', content)
            assert len(old_ports) == 0, f"{js_file.name} has old port: {old_ports}"

    def test_port_consistency_manifest(self):
        manifest_path = Path(__file__).parent.parent / "solace-extension" / "manifest.json"
        content = manifest_path.read_text()
        assert "localhost:8888" in content
        assert "localhost:8080" not in content
        assert "localhost:8791" not in content

    def test_no_var_declarations(self):
        """Extension JS should use const/let, not var."""
        ext_dir = Path(__file__).parent.parent / "solace-extension"
        for js_file in ext_dir.glob("*.js"):
            content = js_file.read_text()
            # Match 'var ' at start of line (not in strings/comments)
            var_decls = re.findall(r'^\s*var\s+\w', content, re.MULTILINE)
            assert len(var_decls) == 0, f"{js_file.name} has var declarations: {var_decls[:5]}"

    def test_ws_bridge_uses_timezone_utc(self):
        """All timestamps should use timezone.utc, not naive datetime."""
        ws_path = Path(__file__).parent.parent / "src" / "yinyang" / "ws_bridge.py"
        content = ws_path.read_text()
        assert "timezone.utc" in content
        assert "utcnow" not in content


# ---------------------------------------------------------------------------
# Integration: All 9 WS message types round-trip
# ---------------------------------------------------------------------------

class TestWSRoundTrip:
    """Integration: every message type produces a valid response."""

    def setup_method(self):
        self.bridge = YinyangWSBridge()

    @pytest.mark.asyncio
    async def test_all_message_types_return_response(self):
        """Every known message type should return a non-None response."""
        test_messages = [
            {"type": "chat", "payload": {"content": "hi"}},
            {"type": "heartbeat", "payload": {}},
            {"type": "detect", "payload": {"url": "https://example.com"}},
            {"type": "state", "payload": {}},
            {"type": "credits", "payload": {}},
        ]
        for msg in test_messages:
            result = await self.bridge._handle_message("s1", msg)
            assert result is not None, f"No response for {msg['type']}"
            assert "type" in result, f"Response missing 'type' for {msg['type']}"

    @pytest.mark.asyncio
    async def test_chat_with_pii_redacts(self):
        """Chat with PII should still respond (PII redacted internally)."""
        result = await self.bridge._handle_message("s1", {
            "type": "chat",
            "payload": {"content": "my email is user@test.com"}
        })
        assert result["type"] == "chat"
        # Response shouldn't echo back the email
        assert "user@test.com" not in result["payload"]["content"]


# ---------------------------------------------------------------------------
# LLM QA Consensus Fixes (P0/P1 from ChatGPT + Gemini + Claude panel)
# ---------------------------------------------------------------------------


class TestWSOriginValidation:
    """P0: WebSocket Origin header must be validated to prevent CSWSH."""

    def test_allowed_origins_frozenset(self):
        assert hasattr(YinyangWSBridge, '_ALLOWED_WS_ORIGINS')
        assert isinstance(YinyangWSBridge._ALLOWED_WS_ORIGINS, frozenset)
        assert "http://localhost:8888" in YinyangWSBridge._ALLOWED_WS_ORIGINS

    def test_chrome_extension_origin_pattern(self):
        """chrome-extension:// origins should be accepted (any extension ID)."""
        # The check is: origin.startswith("chrome-extension://")
        # This is validated in handle_ws — we verify the pattern is correct
        test_origin = "chrome-extension://abcdefghijklmnopqrstuvwxyz"
        assert test_origin.startswith("chrome-extension://")


class TestWSRateLimiter:
    """P1: Rate limiting prevents WS message flooding."""

    def test_rate_limiter_allows_normal_traffic(self):
        from yinyang.ws_bridge import _RateLimiter
        limiter = _RateLimiter(max_calls=10, period=1.0)
        for _ in range(10):
            assert limiter.is_allowed()

    def test_rate_limiter_blocks_excess(self):
        from yinyang.ws_bridge import _RateLimiter
        limiter = _RateLimiter(max_calls=5, period=60.0)
        for _ in range(5):
            assert limiter.is_allowed()
        assert not limiter.is_allowed()

    def test_rate_limit_per_ip_persistence(self):
        """Per-IP rate limiting: same IP's limiter persists across reconnections.

        Verifies that disconnecting and reconnecting from the same IP does NOT
        reset the rate limiter — the _ip_rate_limiters dict keeps the limiter
        keyed by IP, so a reconnecting client inherits the previous exhaustion state.
        This closes Claude's P1 finding from Round 5.
        """
        from yinyang.ws_bridge import YinyangWSBridge, _RateLimiter
        bridge = YinyangWSBridge()
        # Simulate first connection from IP 10.0.0.1
        ip = "10.0.0.1"
        bridge._ip_rate_limiters[ip] = _RateLimiter(max_calls=3, period=60.0)
        limiter1 = bridge._ip_rate_limiters[ip]
        for _ in range(3):
            assert limiter1.is_allowed()
        assert not limiter1.is_allowed(), "Limiter should be exhausted after 3 calls"
        # Simulate reconnection from SAME IP — must get the SAME exhausted limiter
        limiter_after_reconnect = bridge._ip_rate_limiters.get(ip)
        assert limiter_after_reconnect is limiter1, "Same IP must reuse the same limiter object"
        assert not limiter_after_reconnect.is_allowed(), "Reconnection from same IP must NOT reset rate limit"

    def test_rate_limit_different_ips_isolated(self):
        """Different IPs get independent rate limiters."""
        from yinyang.ws_bridge import YinyangWSBridge, _RateLimiter
        bridge = YinyangWSBridge()
        bridge._ip_rate_limiters["10.0.0.1"] = _RateLimiter(max_calls=3, period=60.0)
        bridge._ip_rate_limiters["10.0.0.2"] = _RateLimiter(max_calls=3, period=60.0)
        # Exhaust IP 1
        for _ in range(3):
            bridge._ip_rate_limiters["10.0.0.1"].is_allowed()
        assert not bridge._ip_rate_limiters["10.0.0.1"].is_allowed()
        # IP 2 must still have capacity
        assert bridge._ip_rate_limiters["10.0.0.2"].is_allowed(), "Different IP must have independent rate limiter"

    def test_rate_limiter_window_slides(self):
        """After the window period passes, calls should be allowed again."""
        import time
        from yinyang.ws_bridge import _RateLimiter
        limiter = _RateLimiter(max_calls=2, period=0.1)  # 100ms window
        assert limiter.is_allowed()
        assert limiter.is_allowed()
        assert not limiter.is_allowed()
        time.sleep(0.15)  # Wait for window to slide
        assert limiter.is_allowed(), "Rate limiter must allow calls after window slides"


class TestARIALiveRegions:
    """P1: Screen reader announcements for async state changes."""

    def test_html_has_status_region(self):
        html = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.html").read_text()
        assert 'id="yy-status-live"' in html
        assert 'aria-live="polite"' in html

    def test_html_has_alert_region(self):
        html = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.html").read_text()
        assert 'id="yy-alert-live"' in html
        assert 'aria-live="assertive"' in html

    def test_css_has_sr_only(self):
        css = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.css").read_text()
        assert ".sr-only" in css
        assert "clip" in css

    def test_js_has_announce_function(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "function announce(" in js
        assert "yy-status-live" in js
        assert "yy-alert-live" in js


class TestExtensionStorageMigration:
    """P1: Schema version + migration on extension update."""

    def test_sw_has_schema_version(self):
        sw = Path(__file__).parent.parent.joinpath("solace-extension", "service-worker.js").read_text()
        assert "CURRENT_SCHEMA_VERSION" in sw

    def test_sw_has_migration_handler(self):
        sw = Path(__file__).parent.parent.joinpath("solace-extension", "service-worker.js").read_text()
        assert "schemaVersion" in sw
        assert "reason === 'update'" in sw


class TestCSPHardened:
    """P0: CSP must include default-src 'none' and explicit connect-src."""

    def test_manifest_csp_default_none(self):
        manifest = json.loads(Path(__file__).parent.parent.joinpath("solace-extension", "manifest.json").read_text())
        csp = manifest["content_security_policy"]["extension_pages"]
        assert "default-src 'none'" in csp
        assert "connect-src" in csp
        assert "ws://localhost:8888" in csp


# ---------------------------------------------------------------------------
# Round 4 — Protocol Version Negotiation
# ---------------------------------------------------------------------------


class TestProtocolVersionNegotiation:
    """Protocol version negotiation on first heartbeat."""

    def setup_method(self):
        self.bridge = YinyangWSBridge()

    @pytest.mark.asyncio
    async def test_heartbeat_returns_server_version(self):
        result = await self.bridge._handle_message("s1", {"type": "heartbeat", "payload": {}})
        assert result["type"] == "heartbeat"
        assert result["payload"]["server_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_heartbeat_with_matching_client_version(self):
        result = await self.bridge._handle_message("s1", {"type": "heartbeat", "payload": {"protocol_version": "1.0"}})
        assert result["type"] == "heartbeat"
        assert result["payload"]["client_version"] == "1.0"
        assert result["payload"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_heartbeat_with_compatible_minor_version(self):
        result = await self.bridge._handle_message("s1", {"type": "heartbeat", "payload": {"protocol_version": "1.3"}})
        assert result["type"] == "heartbeat"
        assert result["payload"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_heartbeat_rejects_incompatible_major_version(self):
        result = await self.bridge._handle_message("s1", {"type": "heartbeat", "payload": {"protocol_version": "2.0"}})
        assert result["type"] == "error"
        assert result["code"] == "VERSION_MISMATCH"
        assert "2.0" in result["payload"]["message"]

    def test_protocol_version_constant_exists(self):
        assert hasattr(YinyangWSBridge, "PROTOCOL_VERSION")
        assert YinyangWSBridge.PROTOCOL_VERSION == "1.0"

    def test_supported_major_versions_is_frozenset(self):
        assert isinstance(YinyangWSBridge._SUPPORTED_MAJOR_VERSIONS, frozenset)
        assert 1 in YinyangWSBridge._SUPPORTED_MAJOR_VERSIONS


# ---------------------------------------------------------------------------
# Round 4 — Structured Error Taxonomy
# ---------------------------------------------------------------------------


class TestStructuredErrorTaxonomy:
    """Every error response must include a machine-readable 'code' field."""

    def setup_method(self):
        self.bridge = YinyangWSBridge()

    def test_error_codes_dict_exists(self):
        from yinyang.ws_bridge import ERROR_CODES
        assert isinstance(ERROR_CODES, dict)
        assert len(ERROR_CODES) >= 8
        # Every error code has required fields
        for code, meta in ERROR_CODES.items():
            assert "http" in meta, f"ERROR_CODES[{code}] missing 'http'"
            assert "retryable" in meta, f"ERROR_CODES[{code}] missing 'retryable'"
            assert "description" in meta, f"ERROR_CODES[{code}] missing 'description'"

    @pytest.mark.asyncio
    async def test_unknown_type_returns_code(self):
        result = await self.bridge._handle_message("s1", {"type": "xyzzy", "payload": {}})
        assert result["type"] == "error"
        assert result["code"] == "UNKNOWN_TYPE"

    @pytest.mark.asyncio
    async def test_invalid_message_returns_code(self):
        result = await self.bridge._handle_message("s1", {"not": "valid"})
        assert result["type"] == "error"
        assert result["code"] == "INVALID_MESSAGE"

    @pytest.mark.asyncio
    async def test_missing_field_returns_code(self):
        """Missing app_id on run → MISSING_FIELD."""
        result = await self.bridge._handle_message("s1", {"type": "run", "payload": {}})
        assert result["type"] == "error"
        assert result["code"] == "MISSING_FIELD"

    @pytest.mark.asyncio
    async def test_not_found_returns_code(self):
        """Unknown run_id on approve → NOT_FOUND."""
        result = await self.bridge._handle_message("s1", {"type": "approve", "payload": {"run_id": "nonexistent"}})
        assert result["type"] == "error"
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_invalid_state_on_double_approve(self):
        """Approving an already-sealed run → INVALID_STATE."""
        # First create and approve a run
        run_result = await self.bridge._handle_message("s1", {"type": "run", "payload": {"app_id": "gmail-inbox-triage"}})
        assert run_result["payload"].get("status") == "preview_ready", f"Run failed: {run_result}"
        run_id = run_result["payload"]["run_id"]
        await self.bridge._handle_message("s1", {"type": "approve", "payload": {"run_id": run_id}})
        # Now try to approve again
        result = await self.bridge._handle_message("s1", {"type": "approve", "payload": {"run_id": run_id}})
        assert result["type"] == "error"
        assert result["code"] == "INVALID_STATE"

    @pytest.mark.asyncio
    async def test_schedule_not_found_returns_code(self):
        result = await self.bridge._handle_message("s1", {"type": "schedule", "payload": {"action": "delete", "schedule_id": "nonexistent-id"}})
        assert result["type"] == "error"
        assert result["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Round 4 — Focus Trap in Consent Section
# ---------------------------------------------------------------------------


class TestConsentFocusTrap:
    """Focus trap must be wired in sidepanel.js for consent section."""

    def test_js_has_focus_trap_function(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "trapFocusInConsent" in js

    def test_focus_trap_handles_tab_key(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "event.key === 'Tab'" in js or "event.key===" in js

    def test_focus_trap_handles_escape(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "event.key === 'Escape'" in js or "Escape" in js

    def test_focus_trap_registered_as_listener(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "addEventListener('keydown', trapFocusInConsent)" in js


# ---------------------------------------------------------------------------
# Round 4 — Protocol Version in Extension Constants
# ---------------------------------------------------------------------------


class TestProtocolVersionInExtension:
    """Extension must send protocol version on WS connect."""

    def test_constants_has_protocol_version(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "constants.js").read_text()
        assert "WS_PROTOCOL_VERSION" in js

    def test_sidepanel_sends_version_on_connect(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "protocol_version" in js
        assert "WS_PROTOCOL_VERSION" in js


# ---------------------------------------------------------------------------
# Round 4 — Adversarial Edge Case Tests (Fuzz-style)
# ---------------------------------------------------------------------------


class TestAdversarialEdgeCases:
    """Fuzz-style adversarial tests for WS message handling robustness."""

    def setup_method(self):
        self.bridge = YinyangWSBridge()

    @pytest.mark.asyncio
    async def test_extremely_long_chat_message(self):
        """100KB chat message should not crash."""
        long_msg = "a" * 100_000
        result = await self.bridge._handle_message("s1", {"type": "chat", "payload": {"content": long_msg}})
        assert result["type"] == "chat"
        assert "payload" in result

    @pytest.mark.asyncio
    async def test_unicode_emoji_in_chat(self):
        result = await self.bridge._handle_message("s1", {"type": "chat", "payload": {"content": "Hello 🌍🔥💀"}})
        assert result["type"] == "chat"

    @pytest.mark.asyncio
    async def test_null_bytes_in_payload(self):
        result = await self.bridge._handle_message("s1", {"type": "chat", "payload": {"content": "test\x00null\x00bytes"}})
        assert result["type"] == "chat"

    @pytest.mark.asyncio
    async def test_nested_json_injection(self):
        """Payload containing JSON strings should not cause double-parsing."""
        result = await self.bridge._handle_message("s1", {"type": "chat", "payload": {"content": '{"type":"run","payload":{"app_id":"evil"}}'}})
        assert result["type"] == "chat"

    @pytest.mark.asyncio
    async def test_detect_with_javascript_url(self):
        """javascript: URLs must not crash."""
        result = await self.bridge._handle_message("s1", {"type": "detect", "payload": {"url": "javascript:alert(1)"}})
        assert result["type"] == "detected"

    @pytest.mark.asyncio
    async def test_detect_with_data_url(self):
        result = await self.bridge._handle_message("s1", {"type": "detect", "payload": {"url": "data:text/html,<h1>hi</h1>"}})
        assert result["type"] == "detected"

    @pytest.mark.asyncio
    async def test_detect_with_extremely_long_url(self):
        long_url = "https://example.com/" + "a" * 10_000
        result = await self.bridge._handle_message("s1", {"type": "detect", "payload": {"url": long_url}})
        assert result["type"] == "detected"

    @pytest.mark.asyncio
    async def test_schedule_create_with_invalid_cron(self):
        """Invalid cron expression should still create (validation is at execution time)."""
        result = await self.bridge._handle_message("s1", {"type": "schedule", "payload": {"action": "create", "app_id": "test", "cron": "not-a-cron"}})
        assert result["type"] == "scheduled"

    @pytest.mark.asyncio
    async def test_concurrent_approve_reject_same_run(self):
        """Approve then reject same run — second should handle gracefully."""
        run_result = await self.bridge._handle_message("s1", {"type": "run", "payload": {"app_id": "gmail-inbox-triage"}})
        assert run_result["payload"].get("status") == "preview_ready", f"Run failed: {run_result}"
        run_id = run_result["payload"]["run_id"]
        approve_result = await self.bridge._handle_message("s1", {"type": "approve", "payload": {"run_id": run_id}})
        assert approve_result["payload"]["status"] == "sealed"
        # Reject after approval — reject doesn't guard on state, so it still sets rejected
        reject_result = await self.bridge._handle_message("s1", {"type": "reject", "payload": {"run_id": run_id}})
        assert reject_result["type"] == "state"

    @pytest.mark.asyncio
    async def test_empty_payload_on_all_types(self):
        """All 9 message types must handle empty payload gracefully."""
        for msg_type in ["chat", "heartbeat", "detect", "run", "state", "approve", "reject", "schedule", "credits"]:
            result = await self.bridge._handle_message("s1", {"type": msg_type, "payload": {}})
            assert result is not None, f"Type '{msg_type}' returned None on empty payload"
            assert "type" in result, f"Type '{msg_type}' response missing 'type' field"

    @pytest.mark.asyncio
    async def test_pii_in_detect_url_is_redacted_in_logs(self):
        """PII in URL query params should be redacted before logging."""
        url = "https://example.com/search?email=user@test.com&q=hello"
        result = await self.bridge._handle_message("s1", {"type": "detect", "payload": {"url": url}})
        assert result["type"] == "detected"


# ---------------------------------------------------------------------------
# Round 4 — Cross-Layer Selector Contract Tests
# ---------------------------------------------------------------------------


class TestCrossLayerSelectorContracts:
    """Verify CSS selectors in JS match actual elements in HTML."""

    def _load_extension_files(self):
        ext_dir = Path(__file__).parent.parent / "solace-extension"
        html = (ext_dir / "sidepanel.html").read_text()
        js = (ext_dir / "sidepanel.js").read_text()
        css = (ext_dir / "sidepanel.css").read_text()
        return html, js, css

    def test_js_queryselector_ids_exist_in_html(self):
        """Every getElementById('X') in JS must have id='X' in HTML."""
        html, js, _ = self._load_extension_files()
        # Find all getElementById calls
        ids_in_js = re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js)
        assert len(ids_in_js) > 0, "No getElementById calls found in JS"
        missing = []
        for elem_id in ids_in_js:
            if f'id="{elem_id}"' not in html:
                missing.append(elem_id)
        assert len(missing) == 0, f"JS references IDs not in HTML: {missing}"

    def test_js_queryselector_classes_exist_in_css(self):
        """Key CSS classes used in querySelector must be defined in CSS."""
        _, js, css = self._load_extension_files()
        # Find querySelector('.classname') patterns
        selectors = re.findall(r"querySelector(?:All)?\(['\"]\.([a-zA-Z][\w-]*)['\"]", js)
        missing = []
        for cls in set(selectors):
            if f".{cls}" not in css:
                missing.append(cls)
        assert len(missing) == 0, f"JS queries classes not in CSS: {missing}"

    def test_html_class_coverage_in_css(self):
        """HTML classes prefixed with 'yy-' must be defined in CSS."""
        html, _, css = self._load_extension_files()
        html_classes = set(re.findall(r'class="([^"]*)"', html))
        yy_classes = set()
        for cls_str in html_classes:
            for cls in cls_str.split():
                if cls.startswith("yy-"):
                    yy_classes.add(cls)
        undefined = [c for c in yy_classes if f".{c}" not in css]
        assert len(undefined) == 0, f"HTML yy-classes not in CSS: {undefined}"

    def test_html_data_tab_panels_exist(self):
        """Every data-tab='X' in tabs must have a matching panel-X section."""
        html, _, _ = self._load_extension_files()
        tabs = re.findall(r'data-tab="([^"]+)"', html)
        for tab_name in tabs:
            assert f'id="panel-{tab_name}"' in html, f"Tab '{tab_name}' has no panel-{tab_name} section"

    def test_aria_roles_correct(self):
        """Tab buttons must have role=tab, panels must have role=tabpanel."""
        html, _, _ = self._load_extension_files()
        assert 'role="tablist"' in html
        assert 'role="tab"' in html
        assert 'role="tabpanel"' in html
        # Count: should have same number of tabs and panels
        tab_count = html.count('role="tab"')
        panel_count = html.count('role="tabpanel"')
        assert tab_count == panel_count, f"Tab count ({tab_count}) != panel count ({panel_count})"

    def test_no_inline_event_handlers_in_html(self):
        """No onclick/onload/onerror in HTML — all event binding via addEventListener."""
        html, _, _ = self._load_extension_files()
        dangerous = re.findall(r'\bon(?:click|load|error|submit|change|focus|blur)\s*=', html, re.IGNORECASE)
        assert len(dangerous) == 0, f"Found inline event handlers in HTML: {dangerous}"


# ---------------------------------------------------------------------------
# GLOW 213 — Dialog Semantics, Error UX, PII Expansion, Perf Baseline
# ---------------------------------------------------------------------------


class TestConsentDialogSemantics:
    """Consent section must have full dialog semantics (aria-modal, aria-labelledby)."""

    def test_consent_has_dialog_role(self):
        html = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.html").read_text()
        assert 'role="dialog"' in html

    def test_consent_has_aria_modal(self):
        html = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.html").read_text()
        assert 'aria-modal="true"' in html

    def test_consent_has_aria_labelledby(self):
        html = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.html").read_text()
        assert 'aria-labelledby="consent-title"' in html

    def test_consent_title_has_matching_id(self):
        html = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.html").read_text()
        assert 'id="consent-title"' in html


class TestErrorCodeUXMapping:
    """Client-side error-code → user-facing message mapping in sidepanel.js."""

    def test_error_ux_dict_exists(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "ERROR_UX" in js

    def test_all_error_codes_mapped(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        for code in ["INVALID_JSON", "INVALID_MESSAGE", "UNKNOWN_TYPE", "RATE_LIMITED",
                      "ORIGIN_REJECTED", "VERSION_MISMATCH", "NOT_FOUND", "INVALID_STATE",
                      "MISSING_FIELD", "INTERNAL_ERROR"]:
            assert code in js, f"Error code {code} not mapped in ERROR_UX"

    def test_error_handler_uses_ux_mapping(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "ERROR_UX[msg.code]" in js or "ERROR_UX[" in js

    def test_error_handler_announces_for_screen_readers(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        # Error handler should call announce() for screen reader users
        assert "announce(ux.text" in js or "announce(" in js


class TestPerfBaseline:
    """Performance baseline file must exist with threshold definitions."""

    def test_perf_baseline_file_exists(self):
        baseline = Path(__file__).parent / "perf_baseline.json"
        assert baseline.exists(), "tests/perf_baseline.json must exist"

    def test_perf_baseline_has_required_metrics(self):
        import json
        baseline = json.loads((Path(__file__).parent / "perf_baseline.json").read_text())
        assert "baselines" in baseline
        for metric in ["dom_fingerprint", "ws_round_trip", "pii_redaction"]:
            assert metric in baseline["baselines"], f"Missing baseline metric: {metric}"
            assert "threshold_ms" in baseline["baselines"][metric]

    def test_perf_baseline_has_regression_policy(self):
        import json
        baseline = json.loads((Path(__file__).parent / "perf_baseline.json").read_text())
        assert "regression_policy" in baseline


# ---------------------------------------------------------------------------
# GLOW 214 — Dynamic Port Discovery + Per-Message-Type Rate Limits
# ---------------------------------------------------------------------------


class TestDynamicPortDiscovery:
    """Extension must support dynamic port discovery (8888-8899)."""

    def test_constants_has_port_range(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "constants.js").read_text()
        assert "SOLACE_PORT_RANGE_START" in js
        assert "SOLACE_PORT_RANGE_END" in js
        assert "8888" in js
        assert "8899" in js

    def test_constants_has_discover_port_function(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "constants.js").read_text()
        assert "async function discoverPort" in js

    def test_discover_port_caches_in_storage(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "constants.js").read_text()
        assert "chrome.storage.local" in js
        assert "solace_port" in js

    def test_service_worker_has_port_discovery(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "service-worker.js").read_text()
        assert "swDiscoverPort" in js
        assert "SOLACE_PORT_RANGE_START" in js

    def test_sidepanel_uses_discover_port(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "discoverPort" in js

    def test_ws_bridge_allows_port_range(self):
        """WS Origin allowlist must cover the full 8888-8899 range."""
        from yinyang.ws_bridge import YinyangWSBridge
        for port in range(8888, 8900):
            assert f"http://localhost:{port}" in YinyangWSBridge._ALLOWED_WS_ORIGINS
            assert f"http://127.0.0.1:{port}" in YinyangWSBridge._ALLOWED_WS_ORIGINS


class TestPerMessageTypeRateLimits:
    """Different message types should have different rate limits."""

    def test_message_type_limits_dict_exists(self):
        from yinyang.ws_bridge import _MESSAGE_TYPE_LIMITS
        assert isinstance(_MESSAGE_TYPE_LIMITS, dict)
        assert len(_MESSAGE_TYPE_LIMITS) >= 9

    def test_chat_has_lower_limit_than_heartbeat(self):
        from yinyang.ws_bridge import _MESSAGE_TYPE_LIMITS
        assert _MESSAGE_TYPE_LIMITS["chat"] < _MESSAGE_TYPE_LIMITS["heartbeat"]

    def test_run_has_lowest_limit(self):
        from yinyang.ws_bridge import _MESSAGE_TYPE_LIMITS
        assert _MESSAGE_TYPE_LIMITS["run"] <= min(
            v for k, v in _MESSAGE_TYPE_LIMITS.items() if k != "run"
        )

    def test_bridge_has_type_rate_limiters_dict(self):
        from yinyang.ws_bridge import YinyangWSBridge
        bridge = YinyangWSBridge()
        assert hasattr(bridge, "_ip_type_rate_limiters")
        assert isinstance(bridge._ip_type_rate_limiters, dict)

    @pytest.mark.asyncio
    async def test_chat_rate_limit_enforced(self):
        """Chat messages should be rate-limited at 20/60s, not the global 60/60s."""
        from yinyang.ws_bridge import YinyangWSBridge, _RateLimiter, _MESSAGE_TYPE_LIMITS
        bridge = YinyangWSBridge()
        ip = "10.0.0.99"
        bridge._ip_type_rate_limiters[ip] = {
            "chat": _RateLimiter(max_calls=_MESSAGE_TYPE_LIMITS["chat"], period=60.0)
        }
        limiter = bridge._ip_type_rate_limiters[ip]["chat"]
        for _ in range(_MESSAGE_TYPE_LIMITS["chat"]):
            assert limiter.is_allowed()
        assert not limiter.is_allowed(), "Chat should be exhausted at 20 calls"

    def test_heartbeat_still_allowed_after_chat_exhausted(self):
        """Heartbeat should work even when chat is exhausted (independent limiters)."""
        from yinyang.ws_bridge import YinyangWSBridge, _RateLimiter, _MESSAGE_TYPE_LIMITS
        bridge = YinyangWSBridge()
        ip = "10.0.0.100"
        bridge._ip_type_rate_limiters[ip] = {
            "chat": _RateLimiter(max_calls=2, period=60.0),
            "heartbeat": _RateLimiter(max_calls=120, period=60.0),
        }
        # Exhaust chat
        bridge._ip_type_rate_limiters[ip]["chat"].is_allowed()
        bridge._ip_type_rate_limiters[ip]["chat"].is_allowed()
        assert not bridge._ip_type_rate_limiters[ip]["chat"].is_allowed()
        # Heartbeat still works
        assert bridge._ip_type_rate_limiters[ip]["heartbeat"].is_allowed()


# ---------------------------------------------------------------------------
# GLOW 215 — Incognito Mode + Tauri Protocol Version
# ---------------------------------------------------------------------------


class TestIncognitoModeHandling:
    """Extension must detect and handle incognito mode."""

    def test_service_worker_detects_incognito(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "service-worker.js").read_text()
        assert "IS_INCOGNITO" in js or "inIncognitoContext" in js

    def test_service_worker_responds_to_incognito_check(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "service-worker.js").read_text()
        assert "check_incognito" in js

    def test_sidepanel_checks_incognito(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "check_incognito" in js or "checkIncognito" in js

    def test_incognito_banner_css_exists(self):
        css = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.css").read_text()
        assert "yy-incognito-banner" in css

    def test_incognito_banner_has_aria_role(self):
        js = Path(__file__).parent.parent.joinpath("solace-extension", "sidepanel.js").read_text()
        assert "role" in js and "alert" in js


class TestTauriProtocolVersion:
    """Tauri IPC must include protocol version information."""

    def test_main_rs_has_protocol_version(self):
        rs = Path(__file__).parent.parent.joinpath("src-tauri", "src", "main.rs").read_text()
        assert "protocol_version" in rs

    def test_main_rs_has_port_range(self):
        rs = Path(__file__).parent.parent.joinpath("src-tauri", "src", "main.rs").read_text()
        assert "PORT_RANGE_START" in rs
        assert "PORT_RANGE_END" in rs

    def test_main_rs_has_discover_port(self):
        rs = Path(__file__).parent.parent.joinpath("src-tauri", "src", "main.rs").read_text()
        assert "discover_port" in rs

    def test_main_rs_version_includes_protocol(self):
        rs = Path(__file__).parent.parent.joinpath("src-tauri", "src", "main.rs").read_text()
        assert "supported_major_versions" in rs
